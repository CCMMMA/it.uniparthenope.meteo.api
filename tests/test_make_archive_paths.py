"""Unit tests for dependency-explicit forecast archive path construction."""

from __future__ import annotations

import inspect

import pytest

from core.MakeArchivePaths import MakeArchivePaths


def test_make_archive_path_requires_config_and_uses_resolved_domain(monkeypatch):
    """Ensure path construction cannot fall back to a process-global Flask app."""
    observed = []

    class RecordingPlaces:
        def __init__(self, config):
            observed.append(config)

        def get_domain_and_indeces_by_product_and_place(self, prod, place, date):
            assert (prod, place, date) == ("wrf5", "com63049", "20260413Z1200")
            return ("d02", 0, 1, 2, 3)

    monkeypatch.setattr("core.MakeArchivePaths.Places", RecordingPlaces)
    config = {
        "BASE_PATH": "/archive",
        "ARCHIVE": "forecast",
        "BASE_PATH_HISTORY": "/history",
        "HISTORY": "forecast",
    }

    path = MakeArchivePaths.makePath(
        "wrf5",
        "com63049",
        "20260413Z1200",
        config=config,
    )

    assert path == "/archive/wrf5/d02/forecast/2026/04/13/wrf5_d02_20260413Z1200.nc"
    assert observed == [config]
    assert (
        inspect.signature(MakeArchivePaths.makePath).parameters["config"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
    with pytest.raises(TypeError, match="config"):
        MakeArchivePaths.makePath("wrf5", "com63049", "20260413Z1200")


def test_make_archive_path_supports_coordinates_and_explicit_history_false(monkeypatch):
    """Coordinate lookup and false history flags both select a valid archive."""

    class CoordinatePlaces:
        def __init__(self, config):
            self.config = config

        def get_domain_by_product_and_ll(self, prod, lat, lon):
            assert (prod, lat, lon) == ("wrf5", 40.8, 14.2)
            return "d03"

    monkeypatch.setattr("core.MakeArchivePaths.Places", CoordinatePlaces)
    config = {
        "BASE_PATH": "/archive",
        "ARCHIVE": "forecast",
        "BASE_PATH_HISTORY": "/history",
        "HISTORY": "forecast",
    }

    current = MakeArchivePaths.makePath(
        "wrf5", date="20260413Z1200", history=False, lat=40.8, lon=14.2, config=config
    )
    historical = MakeArchivePaths.makePath(
        "wrf5", date="20260413Z1200", history=True, lat=40.8, lon=14.2, config=config
    )

    assert current.startswith("/archive/")
    assert historical.startswith("/history/")


def test_make_archive_path_rejects_malformed_dates():
    """Callers receive an actionable error instead of slicing failures."""
    with pytest.raises(ValueError, match="YYYYMMDDZHHMM"):
        MakeArchivePaths.makePath("wrf5", date="2026-04-13", config={})
