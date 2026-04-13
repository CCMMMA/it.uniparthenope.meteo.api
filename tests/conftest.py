"""Pytest fixtures for isolated API endpoint tests."""

from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VARS_CONTROL_DIR = REPO_ROOT / "vars-control-file"
STATIC_IMAGES_DIR = REPO_ROOT / "static" / "images"
LEGAL_PATH = REPO_ROOT / "etc" / "legal.json"
MAPS_PATH = REPO_ROOT / "etc" / "maps.json"
PAGES_PATH = REPO_ROOT / "etc" / "pages.json"


@dataclass
class InvocationTiming:
    """One measured HTTP invocation in the test suite."""

    test_id: str
    method: str
    target: str
    url: str
    elapsed_ms: float
    status_code: int | None


def pytest_addoption(parser):
    """Register optional live endpoint and timing controls."""
    group = parser.getgroup("api-live")
    group.addoption(
        "--live-base-url",
        action="store",
        default=None,
        help="Run the live API contract tests against this base URL.",
    )
    group.addoption(
        "--compare-base-url",
        action="store",
        default=None,
        help="Compare live API responses against this second base URL.",
    )
    group.addoption(
        "--live-timeout",
        action="store",
        type=float,
        default=30.0,
        help="Timeout in seconds for live HTTP invocations.",
    )
    group.addoption(
        "--allow-live-posts",
        action="store_true",
        default=False,
        help="Include POST endpoints in live URL runs. Disabled by default to avoid mutating remote systems.",
    )


def pytest_configure(config):
    """Initialize shared test-run state."""
    config._invocation_timings = []


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print per-invocation wallclock timings at the end of the run."""
    timings = getattr(config, "_invocation_timings", [])
    if not timings:
        return

    terminalreporter.section("API Invocation Timings", sep="-")
    for item in sorted(timings, key=lambda entry: entry.elapsed_ms, reverse=True):
        status = item.status_code if item.status_code is not None else "-"
        terminalreporter.write_line(
            f"{item.elapsed_ms:8.2f} ms  [{item.target}] {item.method} {item.url} -> {status} ({item.test_id})"
        )


@pytest.fixture
def invocation_recorder(request):
    """Record wallclock duration for each HTTP invocation executed by a test."""

    def _record(method: str, target: str, url: str, elapsed_ms: float, status_code: int | None):
        request.config._invocation_timings.append(
            InvocationTiming(
                test_id=request.node.nodeid,
                method=method,
                target=target,
                url=url,
                elapsed_ms=elapsed_ms,
                status_code=status_code,
            )
        )

    return _record


@pytest.fixture(scope="session")
def live_base_url(pytestconfig):
    """Return the optional base URL used for live API validation."""
    value = pytestconfig.getoption("--live-base-url")
    return value.rstrip("/") if value else None


@pytest.fixture(scope="session")
def compare_base_url(pytestconfig):
    """Return the optional second URL used for response comparison."""
    value = pytestconfig.getoption("--compare-base-url")
    return value.rstrip("/") if value else None


@pytest.fixture(scope="session")
def live_timeout(pytestconfig):
    """Return the configured timeout for live HTTP calls."""
    return pytestconfig.getoption("--live-timeout")


@pytest.fixture(scope="session")
def allow_live_posts(pytestconfig):
    """Return whether live POST endpoints are explicitly enabled."""
    return pytestconfig.getoption("--allow-live-posts")


def _write_test_maps(base_dir: Path) -> Path:
    """Create a writable copy of maps.json with local test paths."""
    maps = json.loads(MAPS_PATH.read_text(encoding="utf-8"))

    maps_data_dir = base_dir / "maps-data"
    maps_result_dir = base_dir / "maps-result"
    maps_cache_dir = base_dir / "maps-cache"

    for directory in (maps_data_dir, maps_result_dir, maps_cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    maps["data_path"] = f"{maps_data_dir}/"
    maps["result_path"] = f"{maps_result_dir}/"
    maps["cache_path"] = f"{maps_cache_dir}/"

    maps_path = base_dir / "test_maps.json"
    maps_path.write_text(json.dumps(maps), encoding="utf-8")
    return maps_path


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
    test_maps_path = _write_test_maps(base_dir)

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
                f'MAPS = r"{test_maps_path}"',
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
