"""Endpoint-level unit tests for every public API route in the service.

The route inventory is aligned with the public Swagger surface exposed at
https://api.meteo.uniparthenope.it/swagger.json and is exercised here with
pytest plus Flask's built-in test client.
"""

from __future__ import annotations

import builtins
import io
import time

import pytest
from flask import Response

from tests.api_cases import AUTH_HEADERS, IMAGE_CASES, JSON_GET_CASES, POST_CASES


class DummyDiskCache:
    """In-memory no-op disk cache used by endpoint tests."""

    def get(self, *args, **kwargs):
        """Always behave like a cold cache lookup."""
        return None

    def set(self, *args, **kwargs):
        """Accept cache writes without persisting anything."""
        return None


class FakeMeteoServices:
    """Predictable service double for route-level API tests."""

    def __init__(self, config):
        """Store the Flask configuration for compatibility with the real class."""
        self.config = config

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

    def authentication_login(self, user, password):
        """Return fake login payload."""
        return {"token": "demo-token", "user": {"name": user}, "roles": ["student"]}

    def auth2Token(self, token):
        """Return fake bearer-token payload."""
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

    def get_navbar(self, roles, params):
        """Return fake navbar data."""
        return [{"id": "home", "roles": roles}]

    def get_pages(self, params):
        """Return fake pages list."""
        return [{"id": "about_us"}, {"id": "forecast_help"}]

    def get_page_by_id(self, roles, page, params):
        """Return fake page detail."""
        return {"id": page, "roles": roles, "userId": params.get("userId")}

    def set_page_by_id(self, roles, page, payload, params):
        """Return fake page persistence result."""
        return {"result": "ok", "id": page, "payload": payload, "roles": roles}


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
    import apis.namespace_legal as ns_legal
    import apis.namespace_login as ns_login
    import apis.namespace_places as ns_places
    import apis.namespace_products as ns_products
    import apis.namespace_v2 as ns_v2
    import apis.namespace_webcam as ns_webcam

    fake_meteo_services = FakeMeteoServices(app_module.application.config)
    fake_grib_services = FakeGribServices()
    fake_tiles = FakeTiles()

    monkeypatch.setattr(app_module, "diskcache", DummyDiskCache())
    monkeypatch.setattr(app_module, "cache", None)
    monkeypatch.setattr(app_module, "use_pymemcache", False)
    monkeypatch.setattr(app_module, "use_disk_cached", False)
    monkeypatch.setattr(app_module, "meteo_services", fake_meteo_services)
    monkeypatch.setattr(app_module, "grib_services", fake_grib_services)
    monkeypatch.setattr(app_module, "tiles", fake_tiles)
    monkeypatch.setitem(app_module.application.config, "ENV", "test")

    for module in (ns_apps, ns_places, ns_products, ns_instruments):
        if hasattr(module, "get_resource"):
            monkeypatch.setattr(module, "get_resource", lambda *args, **kwargs: None)
        if hasattr(module, "set_resource"):
            monkeypatch.setattr(module, "set_resource", lambda *args, **kwargs: None)
        if hasattr(module, "load_cached_json"):
            monkeypatch.setattr(
                module,
                "load_cached_json",
                lambda payload, default=None: payload if payload is not None else default,
            )

    monkeypatch.setattr(ns_box, "Box", FakeBox)
    monkeypatch.setattr(ns_instruments, "MeteoServices", FakeMeteoServices)
    monkeypatch.setattr(ns_legal, "MeteoServices", FakeMeteoServices)
    monkeypatch.setattr(ns_login, "LoginServices", FakeLoginServices)
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
        ns_v2.core.RRSResponseHandlers,
        "get_latest_weather_report_jsonify",
        lambda: {"report": "latest"},
    )
    monkeypatch.setattr(
        ns_v2.core.RRSResponseHandlers,
        "get_field_lwr_jsonify",
        lambda field: {field: "value"},
    )
    monkeypatch.setattr(
        ns_v2.core.RRSResponseHandlers,
        "get_all_weather_reports_jsonify",
        lambda: {"reports": [{"id": 1}]},
    )
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

    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        """Serve a deterministic SAIS payload for the apps endpoint."""
        if path == "/project/JsonData/sam3.json":
            return io.StringIO('{"risk":"low","updated":"2026-03-27T00:00:00Z"}')
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)


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


@pytest.mark.parametrize("path,payload,headers,assert_payload", POST_CASES)
def test_post_endpoints(client, path, payload, headers, assert_payload, invocation_recorder):
    """Exercise the public POST endpoints exposed by the API."""
    started = time.perf_counter()
    response = client.post(path, json=payload, headers=headers or {})
    invocation_recorder("POST", "local", path, (time.perf_counter() - started) * 1000.0, response.status_code)

    assert response.status_code == 200
    assert response.is_json
    assert assert_payload(response.get_json())
