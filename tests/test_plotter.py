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
    monkeypatch.setattr(plotter_module, "_SHAPEFILE_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_NETCDF_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_SCIPY_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_PLACES_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_HAVERSINE_IMPORT_ERROR", None)
    monkeypatch.setattr(plotter_module, "_PIL_IMPORT_ERROR", None)

    with pytest.raises(RuntimeError, match="matplotlib/basemap"):
        plotter_module.Plotter._ensure_dependencies()


def test_read_variable_applies_window_to_trailing_dimensions():
    plotter = make_plotter()
    window = (slice(3, 9), slice(1, 5))

    value = plotter._read_variable(FakeNc(), "wind", time_index=0, window=window)

    assert value == ("slice", (0, Ellipsis, slice(3, 9), slice(1, 5)))


def test_axis_window_covers_bounds_with_margin_on_ascending_axis():
    axis = plotter_module.np.arange(0.0, 10.0, 0.5)

    window = plotter_module.Plotter._axis_window(axis, 2.1, 3.9, margin=1)

    assert axis[window][0] <= 2.1 - 0.5
    assert axis[window][-1] >= 3.9 + 0.5
    assert window.stop - window.start < axis.size


def test_axis_window_handles_descending_axis_and_clamps_to_grid():
    axis = plotter_module.np.arange(10.0, 0.0, -0.5)

    window = plotter_module.Plotter._axis_window(axis, 8.9, 20.0, margin=2)

    assert window.start == 0
    assert axis[window].min() <= 8.9
    assert axis[window].max() == 10.0


def test_interpolate_scalar_grid_never_downsamples_a_dense_axis():
    plotter = make_plotter()
    lons, lats = plotter_module.np.meshgrid(
        plotter_module.np.linspace(10.0, 11.0, 6), plotter_module.np.linspace(40.0, 41.0, 20)
    )
    data = plotter_module.np.sin(lons) + plotter_module.np.cos(lats)

    _, _, dense_data = plotter._interpolate_scalar_grid(lons, lats, data, factor=2.0, max_points=10)

    assert dense_data.shape == (20, 10)


def test_resolve_tuning_selects_first_matching_diagonal_range():
    product_map = {
        "config": {
            "d03": [
                {"ge": 0, "lt": 30, "values": {"skip": 2, "scale": 10}},
                {"ge": 30, "values": {"skip": 7, "barb_length": 4}},
            ]
        }
    }

    tuning = plotter_module.Plotter._resolve_tuning(product_map, "d03", 45.0)

    assert tuning == {"skip": 7, "scale": 1, "hpa_tick": 1, "barb_length": 4}
    assert plotter_module.Plotter._resolve_tuning(product_map, "d01", 45.0)["skip"] == 20


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RENDER_DATE = "20260101Z1200"


class FakePlaces:
    """Places stub returning one coastal place on the synthetic grid."""

    def __init__(self, config):
        self.bounds = {"minLat": 40.2, "maxLat": 40.8, "minLon": 14.0, "maxLon": 14.9}

    def get_place_by_id(self, place):
        if place != "pl001":
            return None
        return {"long_name": {"it": "Posto"}, "name": {"it": "Posto"}, **self.bounds}

    def get_domain_and_indeces_by_product_and_place(self, prod, place, date=None):
        return ("d03", 0, 0, 0, 0)


@pytest.fixture
def render_env(tmp_path, monkeypatch):
    """Build a Plotter over a synthetic archive, maps file and shapefiles."""
    pytest.importorskip("mpl_toolkits.basemap")
    netcdf = pytest.importorskip("netCDF4")
    pyshp = pytest.importorskip("shapefile")
    image_module = pytest.importorskip("PIL.Image")
    np = plotter_module.np

    shapes = tmp_path / "shapes"
    shapes.mkdir()
    with pyshp.Writer(str(shapes / "land")) as writer:
        writer.field("name", "C")
        writer.poly([[[14.3, 40.3], [14.3, 40.7], [14.7, 40.7], [14.7, 40.3], [14.3, 40.3]]])
        writer.record("inside")
        writer.poly([[[2.0, 50.0], [2.0, 51.0], [3.0, 51.0], [3.0, 50.0], [2.0, 50.0]]])
        writer.record("far away")
    with pyshp.Writer(str(shapes / "sources")) as writer:
        writer.field("name", "C")
        writer.point(14.5, 40.5)
        writer.record("inside")
        writer.point(1.0, 1.0)
        writer.record("far away")
    logo = tmp_path / "logo.png"
    image_module.new("RGBA", (40, 20), (255, 0, 0, 255)).save(logo)

    archive = tmp_path / "data" / "tst1" / "d03" / "archive" / "2026" / "01" / "01"
    archive.mkdir(parents=True)
    lat = np.arange(39.0, 42.0, 0.05)
    lon = np.arange(13.0, 16.0, 0.05)
    grid_lon, grid_lat = np.meshgrid(lon, lat)
    with netcdf.Dataset(archive / f"tst1_d03_{RENDER_DATE}.nc", "w") as nc:
        nc.createDimension("time", 1)
        nc.createDimension("latitude", lat.size)
        nc.createDimension("longitude", lon.size)
        nc.createVariable("latitude", "f8", ("latitude",))[:] = lat
        nc.createVariable("longitude", "f8", ("longitude",))[:] = lon
        for name, field in (
            ("T", 10 + 10 * np.sin(grid_lon * 3)),
            ("U", 5 * np.cos(grid_lat * 3)),
            ("V", 5 * np.sin(grid_lon * 3)),
        ):
            nc.createVariable(name, "f4", ("time", "latitude", "longitude"))[0] = field

    layers = [
        {"type": "shaded", "colormap": "tst1.t", "var1": "T", "time": 0, "text": {"en-US": "T"}},
        {"type": "contour", "var1": "T", "time": 0, "clev_min": 0, "clev_max": 20, "colors": "green"},
        {"type": "versor", "var1": "U", "var2": "V", "time": 0},
        {"type": "barbs", "var1": "U", "var2": "V", "time": 0},
        {"type": "angle", "var1": "T", "time": 0},
        {"type": "shapefiles", "shapefiles": [
            {"path": str(shapes / "land"), "color": "black", "fillcolor": "lightyellow"},
            {"path": str(shapes / "sources"), "color": "magenta", "marker": {"symbol": "+", "size": 4}},
            {"path": str(shapes / "missing"), "color": "red"},
        ]},
    ]
    maps = {
        "title": {"en-US": "%d-%m-%Y %H:%M UTC\n__name__"},
        "data_path": str(tmp_path / "data") + "/",
        "result_path": str(tmp_path / "images"),
        "cache_path": str(tmp_path / "cache"),
        "shapefiles": [{"path": str(shapes / "land"), "color": "black"}],
        "colormaps": {
            "tst1.t": {
                "clevs": [0, 5, 10, 15, 20],
                "ccols": [[0, 0, 255, 255], [0, 255, 255, 255], [0, 255, 0, 255], [255, 255, 0, 255], [255, 0, 0, 255]],
            }
        },
        "products": {
            "tst1": {
                "config": {"d03": [{"ge": 0, "values": {"skip": 4, "scale": 4, "hpa_tick": 5, "barb_length": 4}}]},
                "outputs": {
                    "gen": {"plot": {"layers": layers}},
                    "genW": {"plot": {"layers": layers + [
                        {"type": "watermarks", "watermarks": [{"path": str(logo), "opacity": 0.5, "dim": 0.2}]}
                    ]}},
                },
            }
        },
    }
    maps_file = tmp_path / "maps.json"
    maps_file.write_text(plotter_module.json.dumps(maps))

    monkeypatch.setattr(plotter_module, "Places", FakePlaces)
    plotter = plotter_module.Plotter({"MAPS": str(maps_file), "NOIMAGE_PATH": "/images/noimage.png"})
    return plotter, tmp_path


def rendered_file(tmp_path, relative_path, image_name):
    return tmp_path / "images" / relative_path / image_name


def test_render_publishes_complete_png_and_place_caches(render_env):
    plotter, tmp_path = render_env

    relative_path, image_name = plotter.render("pl001", "tst1", "gen", RENDER_DATE)

    assert relative_path == "plt/pl001/tst1/2026/01/01"
    assert image_name == f"plt_pl001_tst1_{RENDER_DATE}_gen_1024x768.png"
    result = rendered_file(tmp_path, relative_path, image_name)
    assert result.read_bytes().startswith(PNG_SIGNATURE)
    # Atomic publication leaves no temporary siblings behind.
    assert [path.name for path in result.parent.iterdir()] == [image_name]
    assert sorted(path.name for path in (tmp_path / "cache").iterdir()) == [
        "pl001.land.shp.pkl", "pl001.pkl", "pl001.sources.shp.pkl",
    ]
    assert plotter_module.plt.get_fignums() == []


def test_render_clips_shapefile_geometry_to_place_and_reuses_it(render_env, monkeypatch):
    plotter, tmp_path = render_env
    plotter.render("pl001", "tst1", "gen", RENDER_DATE)

    place_map = plotter._place_maps["pl001"]
    land = next(value for key, value in place_map.shapes.items() if key.endswith("land"))
    sources = next(value for key, value in place_map.shapes.items() if key.endswith("sources"))
    assert len(land["rings"]) == 1
    assert sources["points"].shape == (1, 2)

    # A second render, even from a fresh process, must not parse shapefiles again.
    def fail(*args, **kwargs):
        raise AssertionError("shapefile parsed again")

    monkeypatch.setattr(plotter_module.Plotter, "_read_shapefile", staticmethod(fail))
    plotter.render("pl001", "tst1", "gen", RENDER_DATE)
    plotter._place_maps.clear()
    plotter.render("pl001", "tst1", "gen", RENDER_DATE)


def test_render_recovers_from_corrupt_or_stale_basemap_cache(render_env):
    plotter, tmp_path = render_env
    plotter.render("pl001", "tst1", "gen", RENDER_DATE)
    basemap_file = tmp_path / "cache" / "pl001.pkl"

    basemap_file.write_bytes(b"truncated pickle")
    plotter._place_maps.clear()
    plotter.render("pl001", "tst1", "gen", RENDER_DATE)
    assert plotter._place_maps["pl001"].basemap.llcrnrlon == pytest.approx(14.0)

    # Editing the place bounds must not keep serving the old projection.
    plotter.places.bounds["minLon"] = 13.5
    plotter.render("pl001", "tst1", "gen", RENDER_DATE)
    assert plotter._place_maps["pl001"].basemap.llcrnrlon == pytest.approx(13.5)
    plotter._place_maps.clear()
    assert plotter._get_basemap("pl001", 13.5, 40.2, 14.9, 40.8).llcrnrlon == pytest.approx(13.5)


def test_render_applies_watermark(render_env):
    plotter, tmp_path = render_env
    image_module = pytest.importorskip("PIL.Image")

    plain = rendered_file(tmp_path, *plotter.render("pl001", "tst1", "gen", RENDER_DATE))
    marked = rendered_file(tmp_path, *plotter.render("pl001", "tst1", "genW", RENDER_DATE))

    with image_module.open(plain) as plain_image, image_module.open(marked) as marked_image:
        assert marked_image.size == plain_image.size
        assert marked_image.convert("RGBA").tobytes() != plain_image.convert("RGBA").tobytes()


def test_render_returns_noimage_for_unknown_place(render_env):
    plotter, _ = render_env

    assert plotter.render("nowhere", "tst1", "gen", RENDER_DATE) == ("/images/noimage.png", "noimage.png")


def test_render_rejects_unknown_output_before_reading_data(render_env):
    plotter, tmp_path = render_env

    with pytest.raises(plotter_module.PlotConfigurationError, match="nope"):
        plotter.render("pl001", "tst1", "nope", RENDER_DATE)
    assert not (tmp_path / "images").exists()


def test_render_raises_when_archive_file_is_missing(render_env):
    plotter, _ = render_env

    with pytest.raises(plotter_module.DataNotAvailableException):
        plotter.render("pl001", "tst1", "gen", "20260102Z1200")
