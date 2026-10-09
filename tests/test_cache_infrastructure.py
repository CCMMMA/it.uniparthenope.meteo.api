"""Tests for the shared memory and disk cache infrastructure."""

from __future__ import annotations

import hashlib
import json
import os
import time
from types import SimpleNamespace

import pytest

from core.cache_keys import make_cache_key
from core.ManageDiskCache import ManageDiskCache
from core.MemcachedMethodHandlers import _cache_key


def test_cache_layers_share_legacy_compatible_keys():
    """Memory and disk caches must address the same source identically."""
    request = SimpleNamespace(url="https://example.test/forecast?place=napoli")
    expected = hashlib.md5(request.url.encode("utf-8")).hexdigest()

    assert make_cache_key(request) == expected
    assert _cache_key(request) == expected
    assert ManageDiskCache("/unused")._cache_key(request) == expected


def test_explicit_cache_key_does_not_require_request():
    """Canonical endpoint keys can be generated without a Flask request."""
    assert make_cache_key(override="forecast:wrf5:napoli")
    with pytest.raises(ValueError, match="request is required"):
        make_cache_key()


def test_disk_cache_round_trips_structured_and_binary_entries(tmp_path):
    """Atomic writes preserve the public JSON and image return types."""
    cache = ManageDiskCache(tmp_path)
    request = SimpleNamespace(url="https://example.test/resource")

    cache.set(request, {"result": [1, 2, 3]}, type_file="json")
    assert cache.get(request, ttl=60) == {"result": [1, 2, 3]}

    cache.set(request, b"PNG", type_file="plot", cache_key_source="plot")
    assert cache.get(request, ttl=60, cache_key_source="plot") == b"PNG"
    assert not list(tmp_path.rglob("*.tmp"))


def test_disk_cache_removes_corrupt_and_expired_entries(tmp_path):
    """Unreadable or stale cache entries degrade to misses instead of errors."""
    cache = ManageDiskCache(tmp_path)
    request = SimpleNamespace(url="https://example.test/resource")
    cache_file = cache._cache_file(request, ".json")
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("{broken", encoding="utf-8")

    assert cache.get(request, ttl=60) is None
    assert not cache_file.exists()

    cache_file.write_text(json.dumps({"stale": True}), encoding="utf-8")
    old_time = time.time() - 120
    cache_file.touch()
    os.utime(cache_file, (old_time, old_time))
    assert cache.get(request, ttl=60) is None
    assert not cache_file.exists()


def test_atomic_writer_publishes_complete_files_and_cleans_up_failures(tmp_path):
    """A failed write leaves neither a partial target nor a stray temporary file."""
    from core.atomic_io import write_atomic

    target = tmp_path / "entry.json"
    write_atomic(target, lambda file: file.write("complete"))
    assert target.read_text(encoding="utf-8") == "complete"

    def fail_midway(file):
        file.write("partial")
        raise RuntimeError("writer failed")

    with pytest.raises(RuntimeError, match="writer failed"):
        write_atomic(target, fail_midway)

    assert target.read_text(encoding="utf-8") == "complete"
    assert [path.name for path in tmp_path.iterdir()] == ["entry.json"]


def test_mongo_handlers_reuse_one_client_per_uri(monkeypatch):
    """Place lookups must not open a new MongoDB connection for every query."""
    from core import MongoDbHandlers as mongo_module

    created = []

    class FakeCollection:
        def find_one(self, query, proj):
            return {"id": query["id"]}

    class FakeClient:
        def __init__(self, uri, connect=True):
            created.append((uri, connect))

        def __getitem__(self, name):
            return {"places": FakeCollection()}

    monkeypatch.setattr(mongo_module.pymongo, "MongoClient", FakeClient)
    monkeypatch.setattr(mongo_module, "_clients", {})

    default = mongo_module.MongoDBHandlers({"DATABASE": "db"})
    custom = mongo_module.MongoDBHandlers(
        {"DATABASE": "db", "MONGODB_URI": "mongodb://other:27017/"}
    )

    for _ in range(3):
        assert default.get_query_find_one("places", {"id": "com63049"}, None) == {"id": "com63049"}
    custom.get_query_find_one("places", {"id": "com63049"}, None)

    assert created == [
        ("mongodb://db:27017/", False),
        ("mongodb://other:27017/", False),
    ]


def _popularity_tracker(path, **kwargs):
    from core.RequestPopularityTracker import RequestPopularityTracker

    return RequestPopularityTracker(path, flush_every=1000, flush_interval_seconds=3600, **kwargs)


def test_popularity_counters_are_summed_across_worker_processes(tmp_path):
    """Trackers sharing one file (one per uWSGI worker) must add up, not overwrite."""
    path = tmp_path / "request-popularity.json"
    params = {"date": "20260413Z0000", "hours": 0, "step": 1, "opt": "", "filter": ""}
    first_worker = _popularity_tracker(path)
    second_worker = _popularity_tracker(path)

    for _ in range(3):
        first_worker.record("forecast", "wrf5", "com63049", params)
    for _ in range(2):
        second_worker.record("forecast", "wrf5", "com63049", params)
    second_worker.record("timeseries", "wrf5", "ca001", params)

    first_worker.flush()
    second_worker.flush()
    first_worker.record("forecast", "wrf5", "com63049", params)
    first_worker.flush()

    persisted = {
        (record["endpoint"], record["place"]): record["count"]
        for record in json.loads(path.read_text(encoding="utf-8"))["records"]
    }
    assert persisted == {("forecast", "com63049"): 6, ("timeseries", "ca001"): 1}

    # A worker that never served the request still sees it for rebuilds, and a
    # restarted worker resumes from the shared totals.
    assert first_worker.top_requests(prod="wrf5", endpoint="timeseries")[0]["place"] == "ca001"
    assert _popularity_tracker(path).top_requests(endpoint="forecast")[0]["count"] == 6


def test_popularity_reads_include_unflushed_local_requests(tmp_path):
    """Pending increments stay visible locally and survive a refresh from disk."""
    path = tmp_path / "request-popularity.json"
    params = {"date": "20260413Z0000", "hours": 0, "step": 1, "opt": "", "filter": ""}
    local = _popularity_tracker(path)
    other = _popularity_tracker(path)

    local.record("forecast", "wrf5", "com63049", params)
    other.record("forecast", "wrf5", "com63049", params)
    other.flush()

    assert local.matching_requests(prod="wrf5", place="com63049")[0]["count"] == 2
    assert not path.with_name(path.name + ".tmp").exists()


def test_popularity_tracker_ignores_a_corrupt_file(tmp_path):
    """A damaged counter file must not prevent the application from starting."""
    path = tmp_path / "request-popularity.json"
    path.write_text('{"records": [{"endpoint": "forecast"}, 7]', encoding="utf-8")

    tracker = _popularity_tracker(path)
    tracker.record("forecast", "wrf5", "com63049", {"date": "20260413Z0000"})
    tracker.flush()

    assert [r["count"] for r in json.loads(path.read_text(encoding="utf-8"))["records"]] == [1]


def _model_output_service(tmp_path, monkeypatch, place_indexed=True):
    """Build a MeteoServices instance whose only real dependency is the JSON cache."""
    from core import MeteoServices as meteo_module

    service = meteo_module.MeteoServices.__new__(meteo_module.MeteoServices)
    service.config = {
        "CACHE_JSON": str(tmp_path),
        "TTL_DISKCACHE": 3600,
        "BASE_PATH": str(tmp_path / "missing"),
        "ARCHIVE": "archive",
    }
    service.maps = {"products": {"wrf5": {"fields": {"t2c": {"round": 1}}}}}
    service.places = SimpleNamespace(
        get_place_by_id=lambda place, params=None: {"id": place},
        get_domain_and_indeces_by_product_and_place=lambda *args: (
            ("d01", 0, 1, 0, 1) if place_indexed else None
        ),
    )
    monkeypatch.setattr(
        meteo_module.MakeArchivePaths,
        "makePath",
        staticmethod(lambda *args, **kwargs: str(tmp_path / "missing.nc")),
    )
    return service


def test_model_output_cache_hit_applies_the_requested_options(tmp_path, monkeypatch):
    """One cached hour serves every ``opt`` variant without leaking another's extras."""
    service = _model_output_service(tmp_path, monkeypatch)
    params = {"prod": "wrf5", "place": "com63049", "date": "20260413Z0000"}
    cache_file = service._model_output_cache_path("wrf5", "com63049", params["date"])
    os.makedirs(os.path.dirname(cache_file))
    with open(cache_file, "w", encoding="utf-8") as file:
        json.dump({"result": "ok", "dateTime": params["date"], "t2c": 12.5}, file)

    plain = service.modelOutput(dict(params), use_disk_cached=True)
    decorated = service.modelOutput({**params, "opt": "place,fields"}, use_disk_cached=True)

    assert plain == {"result": "ok", "dateTime": params["date"], "t2c": 12.5}
    assert decorated["place"] == {"id": "com63049"}
    assert decorated["fields"] == {"t2c": {"round": 1}}
    with open(cache_file, encoding="utf-8") as file:
        assert "place" not in json.load(file)


def test_model_output_does_not_cache_errors(tmp_path, monkeypatch):
    """A temporary failure must not be replayed from disk for a whole TTL."""
    service = _model_output_service(tmp_path, monkeypatch, place_indexed=False)
    params = {"prod": "wrf5", "place": "unknown", "date": "20260413Z0000"}

    result = service.modelOutput(params, use_disk_cached=True)

    assert result["result"] == "error"
    assert not os.path.exists(service._model_output_cache_path("wrf5", "unknown", params["date"]))
