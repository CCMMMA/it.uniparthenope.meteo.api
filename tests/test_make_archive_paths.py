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
