"""Pytest fixtures for isolated API endpoint tests."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VARS_CONTROL_DIR = REPO_ROOT / "vars-control-file"
STATIC_IMAGES_DIR = REPO_ROOT / "static" / "images"
LEGAL_PATH = REPO_ROOT / "etc" / "legal.json"
MAPS_PATH = REPO_ROOT / "etc" / "maps.json"
PAGES_PATH = REPO_ROOT / "etc" / "pages.json"


def _write_test_config(base_dir: Path) -> Path:
    """Create a dedicated Flask config file for isolated endpoint tests."""
    diskcache_dir = base_dir / "diskcache"
    opendap_dir = base_dir / "opendap"
    storage_dir = base_dir / "storage"
    prods_dir = base_dir / "prods"
    skewt_dir = base_dir / "skewt"
    json_dir = base_dir / "json"
    history_dir = base_dir / "history"
    noimage_path = base_dir / "noimage.jpg"

    for directory in (
        diskcache_dir,
        opendap_dir,
        storage_dir,
        prods_dir,
        skewt_dir,
        json_dir,
        history_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    noimage_path.write_bytes(b"fake-jpeg")

    config_path = base_dir / "test_settings.py"
    config_path.write_text(
        "\n".join(
            [
                'HOME_URL = "https://api.meteo.uniparthenope.it"',
                'CHART_PAGE = "/chart/chart"',
                'TABLE_PAGE = "/table/table"',
                'FORECAST_PAGE = "/forecast/forecast"',
                f'BASE_PATH = r"{opendap_dir}"',
                f'BASE_STORAGE_PATH = r"{storage_dir}"',
                f'PRODS_PATH = r"{prods_dir}"',
                f'VARS_CONTROL_PATH = r"{VARS_CONTROL_DIR}"',
                'BASE_URL = "https://api.meteo.uniparthenope.it"',
                'DODS_URL = "https://api.meteo.uniparthenope.it/opendap/%s/%s/%s/%s"',
                'WMS_URL = "https://api.meteo.uniparthenope.it/ncWMS2/wms"',
                f'BASE_PRODUCTS = r"{STATIC_IMAGES_DIR}"',
                f'BASE_SKEWT = r"{skewt_dir}"',
                f'CACHE_JSON = r"{json_dir}"',
                f'BASE_DISKCACHE = r"{diskcache_dir}"',
                "TTL_MEMCACHED = 1800",
                "TTL_DISKCACHE = 3600",
                f'NOIMAGE_PATH = r"{noimage_path}"',
                'NOIMAGE_URL = "https://api.meteo.uniparthenope.it/images/noimage.png"',
                'PUB_URL = "https://api.meteo.uniparthenope.it/images"',
                'DATABASE = "ccmmma-database"',
                "NUM_THREADS = 4",
                f'LEGAL = r"{LEGAL_PATH}"',
                f'MAPS = r"{MAPS_PATH}"',
                'LANG = "en-US"',
                f'PAGES = r"{PAGES_PATH}"',
                'HISTORY = "history"',
                'ARCHIVE = "archive"',
                'ENV = "test"',
                f'BASE_PATH_HISTORY = r"{history_dir}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return config_path


@pytest.fixture(scope="session")
def app_module(tmp_path_factory: pytest.TempPathFactory):
    """Import the Flask application with a test-specific configuration."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    config_dir = tmp_path_factory.mktemp("api-config")
    os.environ["APP_SETTINGS"] = str(_write_test_config(config_dir))

    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")
    app_module.application.config.update(TESTING=True)
    return app_module


@pytest.fixture
def client(app_module):
    """Return a Flask test client for the API application."""
    return app_module.application.test_client()
