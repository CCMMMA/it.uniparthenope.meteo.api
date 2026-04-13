"""Shared API endpoint case definitions for local and live tests."""

from __future__ import annotations

import pytest


AUTH_HEADERS = {"Authorization": "Bearer demo-token"}


JSON_GET_CASES = [
    pytest.param("/version", None, lambda data: data["environment"] == "test", id="version"),
    pytest.param("/apps/owm/wrf5/prov/10/552/384.geojson", None, lambda data: data["type"] == "FeatureCollection", id="apps-owm"),
    pytest.param("/apps/sais/index", None, lambda data: data["sam3"]["risk"] == "low", id="apps-sais-index"),
    pytest.param("/box/today/com63049", None, lambda data: data["summary"] == "Sunny", id="box-today"),
    pytest.param("/instruments", None, lambda data: "station-01" in data, id="instruments-list"),
    pytest.param("/instruments/station-01", None, lambda data: data["id"] == "station-01", id="instruments-detail"),
    pytest.param("/legal/disclaimer", None, lambda data: data["title"] == "Disclaimer", id="legal-disclaimer"),
    pytest.param("/legal/privacy", None, lambda data: data["title"] == "Privacy", id="legal-privacy"),
    pytest.param("/places", None, lambda data: data[0]["id"] == "com63049", id="places-list"),
    pytest.param("/places/search/byname/Napoli", None, lambda data: data[0]["id"] == "com63049", id="places-search-byname"),
    pytest.param("/places/search/byname/autocomplete?term=nap", None, lambda data: data[0]["label"] == "Napoli", id="places-autocomplete"),
    pytest.param("/places/com63049", None, lambda data: data["id"] == "com63049", id="places-detail"),
    pytest.param("/places/search/bycoords/40.78783/14.352", None, lambda data: data[0]["id"] == "com63049", id="places-bycoords"),
    pytest.param("/places/search/byboundingbox/40.78/14.35/41.22/16.87", None, lambda data: data[0]["id"] == "com63049", id="places-boundingbox"),
    pytest.param("/products", None, lambda data: data["products"] == ["wrf5", "ww33"], id="products-list"),
    pytest.param("/products/wrf5/com63049/avail", None, lambda data: data["avail"]["available"] is True, id="products-avail"),
    pytest.param("/products/wrf5/com63049/avail/calendar", None, lambda data: data["events"][0]["title"] == "wrf5 forecast", id="products-avail-calendar"),
    pytest.param("/products/maps", None, lambda data: data["maps"][0]["id"] == "main-map", id="products-maps"),
    pytest.param("/products/wrf5/maps/themes", None, lambda data: data["themes"][0]["id"] == "wind", id="products-themes"),
    pytest.param("/products/wrf5", None, lambda data: data["outputs"]["id"] == "wrf5", id="products-detail"),
    pytest.param("/products/wrf5/outputs", None, lambda data: data["outputs"][0]["id"] == "gen", id="products-outputs"),
    pytest.param("/products/wrf5/fields", None, lambda data: data["fields"][0]["id"] == "t2c", id="products-fields"),
    pytest.param("/products/wrf5/forecast/com63049", None, lambda data: data["result"] == "ok", id="products-forecast"),
    pytest.param("/products/wrf5/forecast/com63049/plot/alt", None, lambda data: "alt" in data, id="products-plot-alt"),
    pytest.param("/products/wrf5/forecast/d02/grib/json", None, lambda data: data["domain"] == "d02", id="products-grib-json"),
    pytest.param("/products/wrf5/forecast/com63049/plot", None, lambda data: data["map"]["link"].endswith("/wrf5/com63049.png"), id="products-plot"),
    pytest.param("/products/wrf5/plot/gen/metacharts", None, lambda data: data["output"] == "gen", id="products-metacharts"),
    pytest.param("/products/wrf5/timeseries/com63049", None, lambda data: data["result"] == "ok", id="products-timeseries"),
    pytest.param("/v2/weatherreports/latest/json", None, lambda data: data["report"] == "latest", id="v2-weatherreports-latest"),
    pytest.param("/v2/weatherreports/latest/title/json", None, lambda data: data["title"] == "value", id="v2-weatherreports-field"),
    pytest.param("/v2/weatherreports/json", None, lambda data: data["reports"][0]["id"] == 1, id="v2-weatherreports-all"),
    pytest.param("/v2/slurm/storage", None, lambda data: data["status"] == "ok", id="v2-slurm-storage"),
    pytest.param("/v2/slurm/info", None, lambda data: data["nodes"] == 4, id="v2-slurm-info"),
    pytest.param("/v2/slurm/queue", None, lambda data: data["jobs"] == [], id="v2-slurm-queue"),
    pytest.param("/v2/carousel", AUTH_HEADERS, lambda data: data["carousel"][0]["id"] == "hero", id="v2-carousel"),
    pytest.param("/v2/cards", AUTH_HEADERS, lambda data: data["cards"][0]["id"] == "card-1", id="v2-cards"),
    pytest.param("/v2/basemaps", None, lambda data: "demo" in data, id="v2-basemaps"),
    pytest.param("/v2/basemaps/demo", None, lambda data: data["id"] == "demo", id="v2-basemap-detail"),
    pytest.param("/v2/layers", None, lambda data: "info" in data, id="v2-layers"),
    pytest.param("/v2/layers/info", None, lambda data: data["id"] == "info", id="v2-layer-detail"),
    pytest.param("/v2/maps", None, lambda data: "weather" in data, id="v2-maps"),
    pytest.param("/v2/maps/weather", None, lambda data: data["id"] == "weather", id="v2-map-detail"),
    pytest.param("/v2/navbar", AUTH_HEADERS, lambda data: data["navbar"][0]["id"] == "home", id="v2-navbar"),
    pytest.param("/v2/pages", AUTH_HEADERS, lambda data: data["pages"][0]["id"] == "about_us", id="v2-pages"),
    pytest.param("/v2/pages/about_us", AUTH_HEADERS, lambda data: data["id"] == "about_us", id="v2-page-detail"),
    pytest.param("/v2/auth/login", AUTH_HEADERS, lambda data: data["token"] == "demo-token", id="v2-auth-login"),
]


IMAGE_CASES = [
    pytest.param("/products/wrf5/forecast/com63049/plot/image", "image/png", b"plot-image", id="products-plot-image"),
    pytest.param("/products/wrf5/forecast/plot/SkewT/image", "image/png", b"skewt-image", id="products-skewt-image"),
    pytest.param("/products/wrf5/forecast/legend/right/waveheight", "image/png", b"legend-image", id="products-legend"),
    pytest.param("/products/wrf5/forecast/legend/right/waveheight/ncwms", "image/png", b"legend-image-ncwms", id="products-legend-ncwms"),
    pytest.param("/products/wrf5/forecast/com63049/map/image", "image/png", b"legacy-map-image", id="products-legacy-map-image"),
    pytest.param("/products/resource/forecast/sunny.png", "image/png", b"icon-image", id="products-static-icon"),
    pytest.param("/webcam/com63049/castelsantelmo/nord", "image/jpg", b"webcam-image", id="webcam"),
]


POST_CASES = [
    pytest.param(
        "/users/login",
        {"name": "student", "pass": "secret"},
        None,
        lambda data: data["user"]["name"] == "student",
        id="users-login",
    ),
    pytest.param(
        "/v2/pages/about_us",
        {"_id": "about_us", "author": "teacher-01"},
        AUTH_HEADERS,
        lambda data: data["result"] == "ok",
        id="v2-page-upsert",
    ),
]
