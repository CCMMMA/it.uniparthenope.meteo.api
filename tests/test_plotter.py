"""Focused unit tests for Plotter helper behavior."""

from __future__ import annotations

import pytest

import core.Plotter as plotter_module


class FakeVariable:
    """Tiny array-like variable stub for NetCDF slicing tests."""

    def __getitem__(self, key):
        return ("slice", key)


class FakeNc:
    """Container exposing a NetCDF-like variables mapping."""

    def __init__(self):
        self.variables = {"wind": FakeVariable()}


def make_plotter():
    """Create a Plotter instance without running dependency-heavy init."""
    return plotter_module.Plotter.__new__(plotter_module.Plotter)


def test_get_localized_value_prefers_exact_match():
    plotter = make_plotter()

    value = plotter._get_localized_value({"en-US": "Wind", "en": "Fallback"}, "en-US")

    assert value == "Wind"


def test_get_localized_value_falls_back_to_language_prefix():
    plotter = make_plotter()

    value = plotter._get_localized_value({"it-IT": "Vento", "en-US": "Wind"}, "it")

    assert value == "Vento"


def test_get_localized_value_falls_back_to_first_available_value():
    plotter = make_plotter()

    value = plotter._get_localized_value({"fr-FR": "Vent", "en-US": "Wind"}, "de-DE", "Default")

    assert value == "Vent"


def test_read_variable_returns_requested_time_and_level_slice():
    plotter = make_plotter()

    value = plotter._read_variable(FakeNc(), "wind", time_index=2, level_index=4)

    assert value == ("slice", (2, 4))


def test_read_variable_returns_none_for_empty_variable_name():
    plotter = make_plotter()

    assert plotter._read_variable(FakeNc(), "") is None


def test_interpolate_scalar_grid_increases_resolution_and_preserves_edges():
    plotter = make_plotter()
    lon_axis = plotter_module.np.array([10.0, 11.0, 12.0, 13.0])
    lat_axis = plotter_module.np.array([40.0, 41.0, 42.0, 43.0])
    lons, lats = plotter_module.np.meshgrid(lon_axis, lat_axis)
    data = plotter_module.np.arange(16, dtype=float).reshape(4, 4)

    dense_lons, dense_lats, dense_data = plotter._interpolate_scalar_grid(lons, lats, data, factor=2.0, max_points=12)

    assert dense_data.shape == (8, 8)
    assert dense_lons.shape == (8, 8)
    assert dense_lats.shape == (8, 8)
    assert dense_lons[0, 0] == pytest.approx(10.0)
    assert dense_lons[0, -1] == pytest.approx(13.0)
    assert dense_lats[0, 0] == pytest.approx(40.0)
    assert dense_lats[-1, 0] == pytest.approx(43.0)


def test_interpolate_scalar_grid_returns_original_when_factor_not_needed():
    plotter = make_plotter()
    lon_axis = plotter_module.np.array([10.0, 11.0])
    lat_axis = plotter_module.np.array([40.0, 41.0])
    lons, lats = plotter_module.np.meshgrid(lon_axis, lat_axis)
    data = plotter_module.np.array([[1.0, 2.0], [3.0, 4.0]])

    same_lons, same_lats, same_data = plotter._interpolate_scalar_grid(lons, lats, data, factor=1.0, max_points=10)

    assert same_lons is lons
    assert same_lats is lats
    assert same_data is data


def test_ensure_dependencies_raises_clear_error(monkeypatch):
    monkeypatch.setattr(plotter_module, "_PLOTTING_IMPORT_ERROR", ImportError("matplotlib missing"))
    monkeypatch.setattr(plotter_module, "_NETCDF_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_SCIPY_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_PLACES_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_HAVERSINE_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_PIL_IMPORT_ERROR", None)

    with pytest.raises(RuntimeError, match="matplotlib/basemap"):
        plotter_module.Plotter._ensure_dependencies()
