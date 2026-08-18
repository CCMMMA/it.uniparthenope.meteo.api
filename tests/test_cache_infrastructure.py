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
