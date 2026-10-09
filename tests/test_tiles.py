"""Unit tests for weather-tile generation and its API route."""

from __future__ import annotations

import importlib
from dataclasses import replace

import pytest

tiles_module = importlib.import_module("core.Tiles")

PLACES = [
    {"id": "provna", "pos": {"coordinates": [14.27, 40.85]}, "long_name": {"it": "Napoli"}},
    {"id": "eurofr01", "pos": {"coordinates": [2.35, 48.85]}},
    {"id": "provsa", "pos": {"coordinates": [14.77, 40.68]}, "long_name": {"it": "Salerno"}},
]


class FakePlaces:
    """Places stub recording the bounding-box queries it receives."""

    def __init__(self, config):
        self.queries = []
        self.items = list(PLACES)

    def get_places_by_bb(self, lon_min, lat_min, lon_max, lat_max, options=None):
        self.queries.append((lon_min, lat_min, lon_max, lat_max, options))
        return self.items


class FakeMeteo:
    """Forecast stub answering per place from a mapping."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def modelOutput(self, params):
        self.calls.append(dict(params))
        answer = self.answers.get(params["place"], {"result": "ok", "t2c": 21.5})
        if isinstance(answer, Exception):
            raise answer
        return dict(answer)


def make_tiles(monkeypatch, answers=None):
    monkeypatch.setattr(tiles_module, "Places", FakePlaces)
    return tiles_module.Tiles({"NUM_THREADS": 4}, FakeMeteo(answers))


def test_tile_bounding_box_matches_slippy_map_grid(monkeypatch):
    tiles = make_tiles(monkeypatch)

    whole_world = tiles.to_bb(0, 0, 0)
    naples = tiles.to_bb(10, 552, 384)

    assert whole_world["lon_min"] == pytest.approx(-180.0)
    assert whole_world["lon_max"] == pytest.approx(180.0)
    assert whole_world["lat_max"] == pytest.approx(85.0511, abs=1e-4)
    assert whole_world["lat_min"] == pytest.approx(-85.0511, abs=1e-4)
    assert naples["lon_min"] < 14.27 < naples["lon_max"]
    assert naples["lat_min"] < 40.85 < naples["lat_max"]


def test_tile_contains_one_valid_feature_per_place_in_query_order(monkeypatch):
    tiles = make_tiles(monkeypatch)

    tile, cacheable = tiles.get_weather_tile("wrf5", "prov-euro", {"date": "20260814Z1200"}, 10, 552, 384)

    assert cacheable is True
    assert tile["type"] == "FeatureCollection"
    assert [feature["properties"]["id"] for feature in tile["features"]] == ["provna", "eurofr01", "provsa"]
    first, second, _ = tile["features"]
    assert first["geometry"] == {"type": "Point", "coordinates": [14.27, 40.85]}
    assert first["properties"] == {
        "id": "provna", "name": "Napoli", "country": "it", "result": "ok", "t2c": 21.5,
    }
    # A place without a localized name falls back to its id.
    assert second["properties"]["name"] == "eurofr01"
    assert second["properties"]["country"] == "fr"
    assert tiles.places.queries[0][4] == {"filter": ["prov", "euro"], "zoom": 10}
    assert {call["date"] for call in tiles.meteo_services.calls} == {"20260814Z1200"}


def test_tile_omits_places_without_forecast(monkeypatch):
    tiles = make_tiles(monkeypatch, {"eurofr01": {"result": "error", "details": "Place not indexed"}})

    tile, cacheable = tiles.get_weather_tile("wrf5", "prov", {"date": "20260814Z1200"}, 10, 552, 384)

    assert [feature["properties"]["id"] for feature in tile["features"]] == ["provna", "provsa"]
    # The place will never have data for this product, so the tile is final.
    assert cacheable is True
    assert tiles.get_weather_ex("wrf5", "prov", {"date": "20260814Z1200"}, 10, 552, 384) == tile


def test_tile_is_not_cacheable_while_forecast_data_is_pending(monkeypatch):
    tiles = make_tiles(monkeypatch, {"provsa": {"result": "error", "details": "Data not available"}})

    tile, cacheable = tiles.get_weather_tile("wrf5", "prov", {"date": "20260814Z1200"}, 10, 552, 384)

    assert [feature["properties"]["id"] for feature in tile["features"]] == ["provna", "eurofr01"]
    assert cacheable is False


def test_tile_propagates_unexpected_place_failures(monkeypatch):
    tiles = make_tiles(monkeypatch, {"provsa": RuntimeError("mongo down")})

    with pytest.raises(RuntimeError, match="mongo down"):
        tiles.get_weather_tile("wrf5", "prov", {"date": "20260814Z1200"}, 10, 552, 384)


def test_tile_defaults_to_current_utc_hour(monkeypatch):
    tiles = make_tiles(monkeypatch)

    class FixedDatetime(tiles_module.datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is tiles_module.datetime.timezone.utc, "tile dates must be UTC"
            return cls(2026, 8, 14, 9, 47, tzinfo=tz)

    monkeypatch.setattr(tiles_module.datetime, "datetime", FixedDatetime)
    params = {"date": None}

    tiles.get_weather_tile("wrf5", "prov", params, 10, 552, 384)

    assert params["date"] == "20260814Z0900"


@pytest.mark.parametrize("z, x, y", [(23, 0, 0), (2000, 0, 0), (3, 8, 0), (3, 0, 8), (0, 1, 0)])
def test_tile_rejects_addresses_outside_the_grid(monkeypatch, z, x, y):
    tiles = make_tiles(monkeypatch)

    with pytest.raises(tiles_module.InvalidTileError):
        tiles.get_weather_tile("wrf5", "prov", {"date": None}, z, x, y)
    assert tiles.places.queries == []


@pytest.mark.parametrize("placeprefix", ["", "prov-", ".*", "com(a+)+", "prov|"])
def test_tile_rejects_prefixes_that_would_alter_the_place_query(monkeypatch, placeprefix):
    tiles = make_tiles(monkeypatch)

    with pytest.raises(tiles_module.InvalidTileError):
        tiles.get_weather_tile("wrf5", placeprefix, {"date": None}, 10, 552, 384)
    assert tiles.places.queries == []


class RecordingCache:
    """Disk-cache stub that always misses and records writes."""

    def __init__(self):
        self.writes = 0

    def get(self, *args, **kwargs):
        return None

    def set(self, *args, **kwargs):
        self.writes += 1


def install_tiles(monkeypatch, app_module, tiles):
    cache = RecordingCache()
    services = app_module.application.extensions[app_module.RUNTIME_SERVICES_EXTENSION]
    monkeypatch.setitem(
        app_module.application.extensions,
        app_module.RUNTIME_SERVICES_EXTENSION,
        replace(services, tiles=tiles, disk_cache=cache, disk_cache_enabled=True, memory_cache_enabled=False),
    )
    return cache


def test_owm_route_returns_400_for_invalid_tile(client, app_module, monkeypatch):
    cache = install_tiles(monkeypatch, app_module, make_tiles(monkeypatch))

    out_of_grid = client.get("/apps/owm/wrf5/prov/3/8/0.geojson")
    bad_prefix = client.get("/apps/owm/wrf5/prov.*/10/552/384.geojson")

    assert out_of_grid.status_code == 400
    assert "message" in out_of_grid.get_json()
    assert bad_prefix.status_code == 400
    assert cache.writes == 0


def test_owm_route_caches_only_complete_tiles(client, app_module, monkeypatch):
    answers = {"provsa": {"result": "error", "details": "Data not available"}}
    tiles = make_tiles(monkeypatch, answers)
    cache = install_tiles(monkeypatch, app_module, tiles)

    pending = client.get("/apps/owm/wrf5/prov/10/552/384.geojson")
    assert pending.status_code == 200
    assert len(pending.get_json()["features"]) == 2
    assert cache.writes == 0

    answers.clear()
    complete = client.get("/apps/owm/wrf5/prov/10/552/384.geojson")
    assert len(complete.get_json()["features"]) == 3
    assert cache.writes == 1


def test_model_output_reports_missing_archive_file_as_unavailable(tmp_path):
    """A forecast file that has not arrived is an error payload, not a crash."""
    from core.MeteoServices import MeteoServices

    class IndexedPlaces:
        def get_domain_and_indeces_by_product_and_place(self, prod, place, date=None):
            return ("d03", 0, 1, 0, 1)

    service = MeteoServices.__new__(MeteoServices)
    service.config = {
        "BASE_PATH": str(tmp_path / "archive"), "ARCHIVE": "archive",
        "CACHE_JSON": str(tmp_path / "json"), "TTL_DISKCACHE": 3600,
    }
    service.default_prod = "wrf5"
    service.default_place = "com63049"
    service.places = IndexedPlaces()
    service.maps = {"products": {"wrf5": {"fields": {"t2c": {"var": "T2C", "time": 0}}}}}
    service._numpy_method_cache = {}

    result = service.modelOutput({"prod": "wrf5", "place": "provna", "date": "20260814Z1200"})

    assert result == {"result": "error", "details": "Data not available"}
    assert not list((tmp_path / "json").rglob("*.json"))
