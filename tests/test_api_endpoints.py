"""Endpoint-level unit tests for every public API route in the service.

The route inventory is aligned with the public Swagger surface exposed at
https://api.meteo.uniparthenope.it/swagger.json and is exercised here with
pytest plus Flask's built-in test client.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace

import pytest
from flask import Response

from tests.api_cases import AUTH_HEADERS, IMAGE_CASES, JSON_GET_CASES


class DummyDiskCache:
    """In-memory no-op disk cache used by endpoint tests."""

    def get(self, *args, **kwargs):
        """Always behave like a cold cache lookup."""
        return None

    def set(self, *args, **kwargs):
        """Accept cache writes without persisting anything."""
        return None

    def delete(self, *args, **kwargs):
        """Pretend that no cached file matched the deletion request."""
        return 0


class FakePopularityTracker:
    """In-memory popularity tracker used by endpoint tests."""

    def __init__(self):
        self.records = []

    def record(self, endpoint, prod, place, params):
        self.records.append(
            {
                "endpoint": endpoint,
                "prod": prod,
                "place": place,
                "params": dict(params),
                "count": 1,
                "last_seen": time.time(),
            }
        )

    def top_requests(self, prod=None, endpoint=None, place=None, limit=None):
        records = [
            record
            for record in self.records
            if (prod is None or record["prod"] == prod)
            and (endpoint is None or record["endpoint"] == endpoint)
            and (place is None or record["place"] == place)
        ]
        return records[: limit or len(records)]

    def matching_requests(self, prod=None, endpoint=None, place=None):
        return self.top_requests(prod=prod, endpoint=endpoint, place=place)


class FakeMeteoServices:
    """Predictable service double for route-level API tests."""

    def __init__(self, config):
        """Store the Flask configuration for compatibility with the real class."""
        self.config = config
        self.maps = {
            "products": {
                "wrf5": {"fields": {"t2c": {}}},
                "ww33": {"fields": {"t2c": {}}},
            }
        }

    def _parse_datetime_ref(self, timeref, round_to_hour=False, default_midnight=False):
        """Return deterministic datetimes for cache-key helpers."""
        if timeref:
            return datetime.strptime(timeref, "%Y%m%dZ%H%M")
        if default_midnight:
            return datetime(2026, 4, 13, 0, 0)
        return datetime(2026, 4, 13, 12, 0 if round_to_hour else 34)

    def _format_datetime_ref(self, value):
        """Return the canonical datetime string used by the real service."""
        return value.strftime("%Y%m%dZ%H%M")

    def _model_output_cache_path(self, prod, place, timeref):
        """Return a deterministic cache path for invalidation tests."""
        return os.path.join("/tmp", f"{prod}_{place}_{timeref}.json")

    def getProds(self, prod=None):
        """Return fake product catalog data."""
        if prod:
            return {"id": prod, "title": f"{prod} product"}
        return ["wrf5", "ww33"]

    def getProductAvail(self, params):
        """Return fake product availability data."""
        return {"prod": params["prod"], "place": params["place"], "available": True}

    def getProductAvailCalendar(self, params):
        """Return fake availability calendar data."""
        return {
            "events": [
                {
                    "title": f'{params["prod"]} forecast',
                    "url": f'{params["baseUrl"]}&place={params["place"]}',
                }
            ]
        }

    def getMaps(self):
        """Return fake map metadata."""
        return [{"id": "main-map"}]

    def getThemes(self, prod):
        """Return fake theme metadata."""
        return [{"id": "wind", "prod": prod}]

    def getOutputs(self, prod):
        """Return fake output metadata."""
        return [{"id": "gen", "prod": prod}]

    def getFields(self, prod):
        """Return fake field metadata."""
        return [{"id": "t2c", "prod": prod}]

    def modelOutput(self, params, use_disk_cached=True):
        """Return fake forecast data."""
        return {
            "result": "ok",
            "forecast": [{"date": params.get("date") or "20260327Z0000"}],
            "place": {"id": params["place"]},
            "fields": ["t2c"],
            "use_disk_cached": use_disk_cached,
        }

    def ModelPlotImage(self, use_disk_cached, params):
        """Return a fake rendered plot image."""
        return (b"plot-image", "plot.png")

    def ModelPlotSkewT(self, use_disk_cached, params):
        """Return a fake Skew-T image."""
        return (b"skewt-image", "skewt.png")

    def MakeJsonAlt(self, prod, long_name, params):
        """Return fake alt-text payload."""
        return {"alt": f"{prod} alt text for {long_name}"}

    def ModelPlotUrl(self, use_disk_cached, params):
        """Return fake plot metadata."""
        return ({"link": f"https://example.test/{params['prod']}/{params['place']}.png"}, "plot.png")

    def getlegenddata(self, prod, position, output, params):
        """Return fake legend bytes."""
        return b"legend-image"

    def getlegenddata1(self, prod, position, output, params):
        """Return fake ncWMS legend bytes."""
        return b"legend-image-ncwms"

    def plotmetacharts(self, prod, output):
        """Return fake metachart payload."""
        return {"prod": prod, "output": output, "charts": ["line"]}

    def timeseries(self, params):
        """Return fake time-series payload."""
        return {
            "result": "ok",
            "place": {"id": params["place"]},
            "fields": ["t2c"],
            "forecast": [{"step": 0, "value": 21.5}],
        }

    def modelmapurl_or_image(self, use_disk_cached, params):
        """Return fake legacy map image bytes."""
        return (b"legacy-map-image", "legacy.png")

    def getLegalDisclaimer(self, params):
        """Return fake disclaimer content."""
        return {"title": "Disclaimer"}

    def getLegalPrivacy(self, params):
        """Return fake privacy content."""
        return {"title": "Privacy"}

    def getInstruments(self):
        """Return fake instruments catalog."""
        return {
            "station-01": {"id": "station-01", "name": "Station 01"},
            "station-02": {"id": "station-02", "name": "Station 02"},
        }


class FakeGribServices:
    """Fake GRIB export service for endpoint tests."""

    def asText(self, params):
        """Return fake text export."""
        return "lon,lat,value\n14.25,40.85,1.0\n"

    def asJson(self, params):
        """Return fake JSON export."""
        return {"grid": [1.0, 2.0], "domain": params["domain"]}


class FakeTiles:
    """Fake tile service for app-facing GeoJSON endpoints."""

    def get_weather_ex(self, prod, placeprefix, params, z, x, y):
        """Return fake GeoJSON tile data."""
        return {
            "type": "FeatureCollection",
            "features": [],
            "tile": {"prod": prod, "placeprefix": placeprefix, "z": z, "x": x, "y": y},
        }


class FakePlaces:
    """Fake places service for search and lookup endpoints."""

    def __init__(self, config):
        """Store configuration for compatibility with the real service."""
        self.config = config

    def get_all_places(self, collection):
        """Return fake place collection."""
        return [
            {"_id": "1", "id": "com63049", "long_name": {"it": "Napoli"}, "cLat": 40.85, "cLon": 14.27},
            {"_id": "2", "id": "ca001", "long_name": {"it": "Caserta"}, "cLat": 41.07, "cLon": 14.33},
        ]

    def get_places_by_name(self, name, params):
        """Return fake name search results."""
        return [
            {"id": "com63049", "long_name": {"it": "Napoli"}},
            {"id": "provna", "long_name": {"it": f"{name} Provincia"}},
        ]

    def get_place_by_id(self, identifier, params=None):
        """Return fake place detail data."""
        return {"id": identifier, "long_name": {"it": "Napoli"}, "cLat": 40.85, "cLon": 14.27}

    def get_places_by_ll(self, longitude, latitude, params):
        """Return fake coordinate search results."""
        return [{"id": "com63049", "distance_km": 0.4, "cLat": latitude, "cLon": longitude}]

    def get_places_by_bb(self, min_longitude, min_latitude, max_longitude, max_latitude, params):
        """Return fake bounding-box results."""
        return [{"id": "com63049", "bbox": [min_longitude, min_latitude, max_longitude, max_latitude]}]


class FakeBox:
    """Fake box service for summary endpoint tests."""

    def get_today(self, params):
        """Return fake daily summary data."""
        return {"summary": "Sunny", "params": params}


class FakeLoginServices:
    """Fake authentication service for login-related endpoints."""

    def __init__(self, config):
        """Store configuration for compatibility with the real service."""
        self.config = config

    def auth2Token(self, token):
        """Return fake bearer-token payload."""
        if not token:
            return {"errMsg": "Token not valid.", "statusCode": 401}
        return {"user": {"userId": "teacher-01"}, "meteo": {"roles": ["editor"]}, "token": token}


class FakeCMS:
    """Fake CMS service for version 2 endpoints."""

    def __init__(self, config):
        """Store configuration for compatibility with the real service."""
        self.config = config

    def get_carousel(self, roles, params):
        """Return fake carousel data."""
        return [{"id": "hero", "roles": roles}]

    def get_cards(self, roles, params):
        """Return fake card data."""
        return [{"id": "card-1", "roles": roles}]

class FakeSlurmServices:
    """Fake Slurm service for version 2 infrastructure endpoints."""

    def __init__(self, config):
        """Store configuration for compatibility with the real service."""
        self.config = config

    def get_storage_status(self):
        """Return fake storage information."""
        return {"filesystem": "storage", "status": "ok"}

    def sinfo(self):
        """Return fake cluster information."""
        return {"nodes": 4, "state": "idle"}

    def squeue(self):
        """Return fake queue information."""
        return {"jobs": []}


def _fake_csvfy(data):
    """Return a deterministic CSV response for time-series downloads."""
    csv_body = "step,value\n0,21.5\n"
    return Response(csv_body, mimetype="text/csv")


@pytest.fixture(autouse=True)
def stub_api_dependencies(monkeypatch, app_module):
    """Replace external integrations with deterministic test doubles."""
    import apis.namespace_apps as ns_apps
    import apis.namespace_box as ns_box
    import apis.namespace_instruments as ns_instruments
    import apis.namespace_places as ns_places
    import apis.namespace_products as ns_products
    import apis.namespace_v2 as ns_v2
    import apis.namespace_webcam as ns_webcam

    fake_meteo_services = FakeMeteoServices(app_module.application.config)
    fake_grib_services = FakeGribServices()
    fake_tiles = FakeTiles()
    fake_disk_cache = DummyDiskCache()
    fake_popularity_tracker = FakePopularityTracker()

    monkeypatch.setattr(app_module, "diskcache", fake_disk_cache)
    monkeypatch.setattr(app_module, "cache", None)
    monkeypatch.setattr(app_module, "use_pymemcache", False)
    monkeypatch.setattr(app_module, "use_disk_cached", False)
    monkeypatch.setattr(app_module, "request_popularity_tracker", fake_popularity_tracker)
    monkeypatch.setattr(app_module, "meteo_services", fake_meteo_services)
    monkeypatch.setattr(app_module, "grib_services", fake_grib_services)
    monkeypatch.setattr(app_module, "tiles", fake_tiles)
    monkeypatch.setitem(app_module.application.config, "ENV", "test")
    runtime_services = app_module.application.extensions[app_module.RUNTIME_SERVICES_EXTENSION]
    monkeypatch.setitem(
        app_module.application.extensions,
        app_module.RUNTIME_SERVICES_EXTENSION,
        replace(
            runtime_services,
            memory_cache=None,
            memory_cache_enabled=False,
            disk_cache=fake_disk_cache,
            disk_cache_enabled=False,
            meteo=fake_meteo_services,
            grib=fake_grib_services,
            tiles=fake_tiles,
            popularity=fake_popularity_tracker,
        ),
    )

    for module in (ns_apps, ns_places, ns_products, ns_instruments):
        if hasattr(module, "get_resource"):
            monkeypatch.setattr(module, "get_resource", lambda *args, **kwargs: None)
        if hasattr(module, "set_resource"):
            monkeypatch.setattr(module, "set_resource", lambda *args, **kwargs: None)
        if hasattr(module, "delete_resource"):
            monkeypatch.setattr(module, "delete_resource", lambda *args, **kwargs: False)
        if hasattr(module, "load_cached_json"):
            monkeypatch.setattr(
                module,
                "load_cached_json",
                lambda payload, default=None: payload if payload is not None else default,
            )

    monkeypatch.setattr(ns_box, "Box", FakeBox)
    monkeypatch.setattr(ns_instruments, "MeteoServices", FakeMeteoServices)
    monkeypatch.setattr(ns_places, "Places", FakePlaces)
    monkeypatch.setattr(ns_products, "Places", FakePlaces)
    monkeypatch.setattr(ns_products, "MeteoServices", FakeMeteoServices)
    monkeypatch.setattr(ns_products, "csvfy", _fake_csvfy)
    monkeypatch.setattr(ns_products.MakeArchivePaths, "makePath", staticmethod(lambda prod, place: f"/tmp/{prod}_{place}.nc"))
    monkeypatch.setattr(ns_v2, "LoginServices", FakeLoginServices)
    monkeypatch.setattr(ns_v2, "CMS", FakeCMS)
    monkeypatch.setattr(ns_v2, "SlurmServices", FakeSlurmServices)
    monkeypatch.setattr(ns_v2, "baseMaps", {"demo": {"id": "demo"}})
    monkeypatch.setattr(ns_v2, "layers", {"info": {"id": "info"}})
    monkeypatch.setattr(ns_v2, "maps", {"weather": {"id": "weather"}})
    monkeypatch.setattr(
        ns_products,
        "send_from_directory",
        lambda base_path, icon: Response(b"icon-image", mimetype="image/png"),
    )
    monkeypatch.setattr(
        ns_webcam,
        "send_file",
        lambda *args, **kwargs: Response(b"webcam-image", mimetype="image/jpg"),
    )

def test_grib_text_endpoint(client, invocation_recorder):
    """Ensure the text-oriented GRIB export endpoint returns plain text."""
    started = time.perf_counter()
    response = client.get("/products/wrf5/forecast/d02/grib/text")
    invocation_recorder("GET", "local", "/products/wrf5/forecast/d02/grib/text", (time.perf_counter() - started) * 1000.0, response.status_code)

    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    assert "lon,lat,value" in response.get_data(as_text=True)


def test_timeseries_csv_endpoint(client, invocation_recorder):
    """Ensure the CSV time-series endpoint returns CSV content."""
    started = time.perf_counter()
    response = client.get("/products/wrf5/timeseries/com63049/csv")
    invocation_recorder("GET", "local", "/products/wrf5/timeseries/com63049/csv", (time.perf_counter() - started) * 1000.0, response.status_code)

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert response.get_data(as_text=True).startswith("step,value")


def test_instrument_detail_missing_uses_legacy_json_string(client):
    """Ensure missing instrument details keep the legacy JSON-string response shape."""
    response = client.get("/instruments/station-99")

    assert response.status_code == 404
    assert response.get_json() == "Identification not found!"


def test_v2_basemap_detail_legacy_alias_matches_canonical_route(client):
    """Ensure the legacy basemap/detail alias still resolves a named basemap."""
    response = client.get("/v2/basemap/detail?name=demo")

    assert response.status_code == 200
    assert response.get_json()["id"] == "demo"


def test_forecast_and_timeseries_requests_are_tracked(client, app_module):
    """Ensure successful forecast and time-series requests are recorded for popularity rebuilds."""
    client.get("/products/wrf5/forecast/com63049")
    client.get("/products/wrf5/timeseries/com63049")

    recorded = app_module.request_popularity_tracker.records
    assert any(item["endpoint"] == "forecast" and item["prod"] == "wrf5" and item["place"] == "com63049" for item in recorded)
    assert any(item["endpoint"] == "timeseries" and item["prod"] == "wrf5" and item["place"] == "com63049" for item in recorded)


def test_invalidate_endpoint_removes_matching_cache_entries(client, app_module, monkeypatch, tmp_path):
    """Ensure the invalidate endpoint clears hourly and top-level caches for the requested window."""
    import apis.namespace_products as ns_products

    class DeletingDiskCache:
        def __init__(self):
            self.deleted = []

        def delete(self, request=None, flag_diskcache=True, cache_key_source=None):
            self.deleted.append(cache_key_source)
            return 1

    tracker = FakePopularityTracker()
    tracker.records = [
        {
            "endpoint": "forecast",
            "prod": "wrf5",
            "place": "com63049",
            "params": {"date": "20260413Z0000", "hours": 0, "step": 1, "opt": "", "filter": ""},
            "count": 3,
            "last_seen": time.time(),
        },
        {
            "endpoint": "timeseries",
            "prod": "wrf5",
            "place": "com63049",
            "params": {"date": "20260413Z0000", "hours": 24, "step": 1, "opt": "", "filter": ""},
            "count": 2,
            "last_seen": time.time(),
        },
    ]

    deleted_memcache_keys = []
    cache_dir = tmp_path / "model-cache"
    cache_dir.mkdir()

    monkeypatch.setattr(app_module, "request_popularity_tracker", tracker)
    monkeypatch.setattr(app_module, "diskcache", DeletingDiskCache())
    monkeypatch.setattr(
        app_module.meteo_services,
        "_model_output_cache_path",
        lambda prod, place, timeref: str(cache_dir / f"{prod}_{place}_{timeref}.json"),
    )
    monkeypatch.setattr(ns_products, "delete_resource", lambda *args, cache_key_override=None, **kwargs: deleted_memcache_keys.append(cache_key_override) or True)

    for timeref in ("20260413Z0000", "20260413Z0100"):
        (cache_dir / f"wrf5_com63049_{timeref}.json").write_text("{}", encoding="utf-8")

    response = client.get("/products/wrf5/invalidate/com63049/?date=20260413Z0000&hours=2")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["result"] == "ok"
    assert payload["deleted_model_output_files"] == 2
    assert payload["matched_popular_requests"] == 2
    assert len(deleted_memcache_keys) == 2


def test_rebuild_endpoint_warms_popular_requests(client, app_module, monkeypatch):
    """Ensure rebuild uses the most popular forecast and time-series signatures for the selected product."""
    import apis.namespace_products as ns_products

    tracker = FakePopularityTracker()
    tracker.records = [
        {
            "endpoint": "forecast",
            "prod": "wrf5",
            "place": "com63049",
            "params": {"date": "20260413Z1200", "hours": 0, "step": 1, "opt": "", "filter": ""},
            "count": 4,
            "last_seen": time.time(),
        },
        {
            "endpoint": "timeseries",
            "prod": "wrf5",
            "place": "ca001",
            "params": {"date": "20260413Z0000", "hours": 24, "step": 3, "opt": "", "filter": ""},
            "count": 3,
            "last_seen": time.time(),
        },
    ]

    warmed_forecasts = []
    warmed_timeseries = []

    monkeypatch.setattr(app_module, "request_popularity_tracker", tracker)
    monkeypatch.setattr(
        ns_products,
        "_warm_forecast_cache",
        lambda prod, place, params: warmed_forecasts.append((prod, place, params["date"])) or {"status": "ok"},
    )
    monkeypatch.setattr(
        ns_products,
        "_warm_timeseries_cache",
        lambda prod, place, params: warmed_timeseries.append((prod, place, params["date"], params["hours"], params["step"])) or {"status": "ok"},
    )

    response = client.get("/products/wrf5/rebuild/?date=20260413Z0000&hours=2&limit=1")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["result"] == "ok"
    assert payload["forecast_candidates"] == 1
    assert payload["timeseries_candidates"] == 1
    assert payload["forecast_rebuilt"] == 2
    assert payload["timeseries_rebuilt"] == 1
    assert warmed_forecasts == [("wrf5", "com63049", "20260413Z0000"), ("wrf5", "com63049", "20260413Z0100")]
    assert warmed_timeseries == [("wrf5", "ca001", "20260413Z0000", 2, 3)]


def test_timeseries_json_and_csv_share_cache_payload(client, app_module, monkeypatch):
    """Ensure JSON and CSV time-series routes reuse the same cached structured payload."""
    import apis.namespace_products as ns_products

    class CountingMeteoServices(FakeMeteoServices):
        def __init__(self, config):
            super().__init__(config)
            self.calls = 0

        def timeseries(self, params):
            self.calls += 1
            return {
                "result": "ok",
                "place": {"id": params["place"]},
                "fields": ["t2c"],
                "timeseries": [{"step": 0, "value": 21.5}],
            }

    class MemoryCache:
        def __init__(self):
            self.values = {}

        def get(self, key):
            return self.values.get(key)

        def set(self, key, value, ttl=None):
            self.values[key] = value

    class MemoryDiskCache:
        def __init__(self):
            self.values = {}

        def get(self, request, ttl, path_archive=None, flag_diskcache=True, cache_key_source=None):
            if not flag_diskcache:
                return None
            return self.values.get(cache_key_source or request.url)

        def set(self, request, res, type_file="plot", flag_diskcache=True, cache_key_source=None):
            if not flag_diskcache:
                return
            self.values[cache_key_source or request.url] = res

    service = CountingMeteoServices(app_module.application.config)
    cache = MemoryCache()
    diskcache = MemoryDiskCache()

    monkeypatch.setattr(app_module, "meteo_services", service)
    monkeypatch.setattr(app_module, "cache", cache)
    monkeypatch.setattr(app_module, "diskcache", diskcache)
    monkeypatch.setattr(app_module, "use_pymemcache", True)
    monkeypatch.setattr(app_module, "use_disk_cached", True)
    monkeypatch.setattr(
        ns_products,
        "get_resource",
        lambda request, cache, use_pymemcache, cache_key_override=None: cache.get(cache_key_override or request.url)
        if use_pymemcache
        else None,
    )
    monkeypatch.setattr(
        ns_products,
        "set_resource",
        lambda request, res, cache, use_pymemcache, ttl, cache_key_override=None: cache.set(
            cache_key_override or request.url,
            res,
            ttl,
        )
        if use_pymemcache
        else None,
    )

    json_response = client.get("/products/wrf5/timeseries/com63049")
    csv_response = client.get("/products/wrf5/timeseries/com63049/csv")

    assert json_response.status_code == 200
    assert csv_response.status_code == 200
    assert service.calls == 1


def test_apps_owm_promotes_disk_cache_hit_to_memcache(client, app_module, monkeypatch):
    """Ensure a tile found on disk is promoted instead of read again next request."""
    import apis.namespace_apps as ns_apps

    tile = {"type": "FeatureCollection", "features": [{"properties": {"id": "provna"}}]}
    memcache = {}

    class DiskHitCache:
        def __init__(self):
            self.reads = 0

        def get(self, request, ttl, path_archive=None, flag_diskcache=True, cache_key_source=None):
            self.reads += 1
            return tile

        def set(self, *args, **kwargs):
            raise AssertionError("an existing disk tile must not be rewritten")

    diskcache = DiskHitCache()
    monkeypatch.setattr(app_module, "cache", memcache)
    monkeypatch.setattr(app_module, "diskcache", diskcache)
    monkeypatch.setattr(app_module, "use_pymemcache", True)
    monkeypatch.setattr(app_module, "use_disk_cached", True)
    monkeypatch.setattr(
        ns_apps,
        "get_resource",
        lambda request, cache, enabled: cache.get(request.url) if enabled else None,
    )
    monkeypatch.setattr(
        ns_apps,
        "set_resource",
        lambda request, value, cache, enabled, ttl: cache.__setitem__(request.url, json.dumps(value))
        if enabled
        else None,
    )

    first = client.get("/apps/owm/wrf5/prov/10/552/384.geojson")
    second = client.get("/apps/owm/wrf5/prov/10/552/384.geojson")

    assert first.get_json() == tile
    assert second.get_json() == tile
    assert diskcache.reads == 1


def test_tiles_reuses_worker_pool_across_cache_misses(app_module, monkeypatch):
    """Ensure tile generation does not recreate its worker pool per request."""
    tiles_module = importlib.import_module("core.Tiles")
    pool_activity = {"created": 0, "maps": 0}

    class FakePlacesForTiles:
        def __init__(self, config):
            pass

        def get_places_by_bb(self, *args, **kwargs):
            return []

    class RecordingExecutor:
        def __init__(self, **kwargs):
            pool_activity["created"] += 1

        def map(self, function, items):
            pool_activity["maps"] += 1
            return map(function, items)

    monkeypatch.setattr(tiles_module, "Places", FakePlacesForTiles)
    monkeypatch.setattr(tiles_module, "ThreadPoolExecutor", RecordingExecutor)

    tiles = tiles_module.Tiles({"NUM_THREADS": 8})
    tiles.places.get_places_by_bb = lambda *args, **kwargs: [
        {"id": "provna", "pos": {"coordinates": [14.27, 40.85]}, "long_name": {"it": "Napoli"}}
    ]
    monkeypatch.setattr(
        app_module.meteo_services,
        "modelOutput",
        lambda params: {"result": "ok", "forecast": []},
    )

    first = tiles.get_weather_ex("wrf5", "prov", {"date": "20260814Z1200"}, 10, 552, 384)
    second = tiles.get_weather_ex("wrf5", "prov", {"date": "20260814Z1200"}, 10, 552, 384)

    assert first == second
    assert pool_activity == {"created": 1, "maps": 2}


def test_timeseries_reuses_model_output_disk_cache(monkeypatch):
    """Ensure the time-series builder loads cached slices locally and computes misses with cache enabled."""
    from core.MeteoServices import MeteoServices

    service = MeteoServices.__new__(MeteoServices)
    service.config = {
        "BASE_PATH": "/tmp/base",
        "ARCHIVE": "archive",
        "NUM_THREADS": 2,
        "TTL_DISKCACHE": 3600,
    }
    service.default_prod = "wrf5"
    service.default_place = "com63049"
    service.maps = {"products": {"wrf5": {"fields": {}}}}
    service.places = SimpleNamespace(
        get_domain_and_indeces_by_product_and_place=lambda prod, place: ("d01", 0, 1, 0, 1)
    )
    service._parse_datetime_ref = lambda timeref, default_midnight=False, round_to_hour=False: __import__(
        "datetime"
    ).datetime(2026, 4, 13, 0, 0)
    service._format_datetime_ref = lambda dt: dt.strftime("%Y%m%dZ%H%M")

    loaded_dates = []
    computed_dates = []

    service._is_model_output_cache_valid = lambda item: item["date"].endswith("0000")
    service._load_timeseries_cached_outputs = lambda items: [
        loaded_dates.append(item["date"]) or {"dateTime": item["date"], "t2c": 1.0}
        for item in items
    ]
    service._compute_timeseries_uncached_outputs = lambda items: [
        computed_dates.append(item["date"]) or {"dateTime": item["date"], "t2c": 1.0}
        for item in items
    ]

    seen_dates = []

    def fake_isfile(path):
        if not path.endswith(".nc"):
            return False
        basename = os.path.basename(path)
        date_token = basename.rsplit("_", 1)[-1].replace(".nc", "")
        if len(seen_dates) < 2:
            seen_dates.append(date_token)
            return True
        return date_token in seen_dates

    monkeypatch.setattr("core.MeteoServices.os.path.isfile", fake_isfile)

    result = service.timeseries({"prod": "wrf5", "place": "com63049"})

    assert result["result"] == "ok"
    assert loaded_dates == ["20260413Z0000"]
    assert computed_dates == ["20260413Z0100"]


def test_timeseries_uncached_outputs_use_process_pool_when_enabled(monkeypatch):
    """Ensure uncached multi-step batches use the process-pool path when configured."""
    from core.MeteoServices import MeteoServices

    service = MeteoServices.__new__(MeteoServices)
    service.config = {
        "MAPS": "/tmp/maps.json",
        "NUM_THREADS": 4,
        "NUM_PROCESSES": 3,
        "TIMESERIES_PARALLEL_MODE": "processes",
    }

    recorded = {}

    class FakeProcessPoolExecutor:
        def __init__(self, max_workers, initializer=None, initargs=()):
            recorded["max_workers"] = max_workers
            recorded["initializer"] = initializer
            recorded["initargs"] = initargs
            if initializer is not None:
                initializer(*initargs)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def map(self, func, items):
            return [func(item) for item in items]

    monkeypatch.setattr("core.MeteoServices.ProcessPoolExecutor", FakeProcessPoolExecutor)
    monkeypatch.setattr(
        "core.MeteoServices._init_timeseries_process_pool",
        lambda config: recorded.setdefault("initialized_with", config),
    )
    monkeypatch.setattr(
        "core.MeteoServices._process_pool_model_output",
        lambda item: {"dateTime": item["date"], "value": 1.0},
    )

    outputs = service._compute_timeseries_uncached_outputs(
        [
            {"prod": "wrf5", "place": "com63049", "date": "20260413Z0000"},
            {"prod": "wrf5", "place": "com63049", "date": "20260413Z0100"},
        ]
    )

    assert [item["dateTime"] for item in outputs] == ["20260413Z0000", "20260413Z0100"]
    assert recorded["max_workers"] == 2
    assert recorded["initialized_with"] == dict(service.config)


@pytest.mark.parametrize("path,headers,assert_payload", JSON_GET_CASES)
def test_json_get_endpoints(client, path, headers, assert_payload, invocation_recorder):
    """Exercise every JSON-style GET endpoint exposed by the public API."""
    started = time.perf_counter()
    response = client.get(path, headers=headers or {})
    invocation_recorder("GET", "local", path, (time.perf_counter() - started) * 1000.0, response.status_code)

    assert response.status_code == 200
    assert response.is_json
    assert assert_payload(response.get_json())


@pytest.mark.parametrize("path,expected_mimetype,expected_body", IMAGE_CASES)
def test_binary_endpoints(client, path, expected_mimetype, expected_body, invocation_recorder):
    """Exercise every binary/image endpoint exposed by the public API."""
    started = time.perf_counter()
    response = client.get(path)
    invocation_recorder("GET", "local", path, (time.perf_counter() - started) * 1000.0, response.status_code)

    assert response.status_code == 200
    assert response.mimetype == expected_mimetype
    assert response.data == expected_body


def test_legacy_users_login_is_not_registered(client):
    """Ensure the retired legacy login endpoint is no longer exposed."""
    response = client.post("/users/login", json={"name": "student", "pass": "secret"})

    assert response.status_code == 404


def test_api_v1_responses_identify_the_contract_version(client):
    """Ensure governed endpoints expose their contract version in a response header."""
    response = client.get("/api/v1")

    assert response.status_code == 200
    assert response.headers["API-Version"] == "1"


def test_application_factory_publishes_runtime_services(app_module):
    """Ensure new handlers can resolve dependencies without importing module globals."""
    import wsgi

    services = app_module.application.extensions[app_module.RUNTIME_SERVICES_EXTENSION]

    assert callable(app_module.create_app)
    assert wsgi.application is app_module.application
    assert services.meteo is app_module.meteo_services
    assert services.grib is app_module.grib_services
    assert services.tiles is app_module.tiles
    assert services.disk_cache is app_module.diskcache
    assert services.popularity is app_module.request_popularity_tracker


def test_legal_handlers_use_the_shared_runtime_service(client, app_module, monkeypatch):
    """Ensure legal requests do not construct a heavyweight MeteoServices per request."""
    services = app_module.application.extensions[app_module.RUNTIME_SERVICES_EXTENSION]
    monkeypatch.setattr(
        services.meteo,
        "getLegalDisclaimer",
        lambda params: {"title": "Disclaimer", "service": "shared"},
    )

    response = client.get("/legal/disclaimer")

    assert response.status_code == 200
    assert response.get_json()["service"] == "shared"


def test_legacy_responses_are_unchanged_by_version_headers(client):
    """Ensure the versioning foundation does not relabel legacy contracts."""
    response = client.get("/version")

    assert response.status_code == 200
    assert "API-Version" not in response.headers


def test_apps_sais_index_is_not_registered(client):
    """Ensure the retired SAIS index endpoint is no longer exposed."""
    response = client.get("/apps/sais/index")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/v2/auth/login",
        "/v2/navbar",
        "/v2/pages",
        "/v2/pages/about",
        "/v2/page/detail?page=about",
        "/v2/weatherreports/latest/json",
        "/v2/weatherreports/latest/title/json",
        "/v2/weatherreports/json",
    ],
)
def test_retired_v2_endpoints_are_not_registered(client, path):
    """Ensure retired version 2 endpoint families are no longer exposed."""
    assert client.get(path, headers=AUTH_HEADERS).status_code == 404


def test_retired_v2_page_write_is_not_registered(client):
    """Ensure the retired CMS page write endpoint is no longer exposed."""
    response = client.post("/v2/pages/about", json={"_id": "about"}, headers=AUTH_HEADERS)

    assert response.status_code == 404
