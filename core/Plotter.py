"""Plot-generation helpers for image-based forecast products."""

from collections import OrderedDict
import datetime
import io
import json
import os
import pickle
import threading

from core.Logger import logger
from core.atomic_io import write_atomic

try:
    import numpy as np
    _NUMPY_IMPORT_ERROR = None
except ImportError as exc:
    np = None
    _NUMPY_IMPORT_ERROR = exc

try:
    import matplotlib
    # Plots are rendered off-screen inside API workers; never pick a GUI backend.
    matplotlib.use("Agg")
    from matplotlib.colors import ListedColormap, BoundaryNorm
    from matplotlib.collections import LineCollection, PolyCollection
    import matplotlib.pyplot as plt
    from mpl_toolkits.basemap import Basemap
    _PLOTTING_IMPORT_ERROR = None
except ImportError as exc:
    ListedColormap = BoundaryNorm = LineCollection = PolyCollection = None
    plt = Basemap = None
    _PLOTTING_IMPORT_ERROR = exc

try:
    import shapefile as pyshp
    _SHAPEFILE_IMPORT_ERROR = None
except ImportError as exc:
    pyshp = None
    _SHAPEFILE_IMPORT_ERROR = exc

try:
    from scipy.ndimage import zoom as scipy_zoom
    _SCIPY_IMPORT_ERROR = None
except ImportError as exc:
    scipy_zoom = None
    _SCIPY_IMPORT_ERROR = exc

try:
    from netCDF4 import Dataset as NetCDFFile
    _NETCDF_IMPORT_ERROR = None
except ImportError as exc:
    NetCDFFile = None
    _NETCDF_IMPORT_ERROR = exc

try:
    from core.Places import Places
    _PLACES_IMPORT_ERROR = None
except ImportError as exc:
    Places = None
    _PLACES_IMPORT_ERROR = exc

try:
    import haversine
    _HAVERSINE_IMPORT_ERROR = None
except ImportError as exc:
    haversine = None
    _HAVERSINE_IMPORT_ERROR = exc

# To watermark
try:
    from PIL import Image, ImageEnhance
    _PIL_IMPORT_ERROR = None
except ImportError as exc:
    Image = ImageEnhance = None
    _PIL_IMPORT_ERROR = exc


# Basemap wrappers call pyplot's "current image" hooks, which are process-global
# state, so only one figure may be under construction at a time.
_RENDER_LOCK = threading.Lock()

# Per-process bound on cached place maps (projection plus clipped shapefiles).
_PLACE_MAP_CACHE_SIZE = 16

# Grid cells read around the place bounds so contours, cubic interpolation and
# wind symbols stay continuous up to the map frame.
_GRID_MARGIN = 2

_POINT_SHAPE_TYPES = frozenset({1, 8, 11, 18, 21, 28})


class DataNotAvailableException(Exception):
    """Exception raised when a requested dataset cannot be plotted."""
    pass


class PlotConfigurationError(Exception):
    """Exception raised when the maps configuration cannot describe a plot."""
    pass


class _PlaceMap(object):
    """Projection and projected shapefile geometry cached for one place."""
    __slots__ = ("basemap", "bounds", "shapes")

    def __init__(self, basemap, bounds):
        self.basemap = basemap
        self.bounds = bounds
        self.shapes = {}


class Plotter(object):
    """Render forecast maps described by the maps configuration file."""
    maps = None
    config = None
    places = None
    data_path = None
    result_path = None
    cache_path = None

    # Constructor
    def __init__(self, config):
        """Initialize plotter state."""
        self._ensure_dependencies()
        self._place_maps = OrderedDict()
        self._watermark_image_cache = {}

        # Set the configuration object
        self.config = config

        # Create a Places instance
        self.places = Places(self.config)

        if "MAPS" not in self.config:
            logger.critical("MAPS not set in the json configuration file.")
            return

        config_file = self.config["MAPS"]
        if not os.path.exists(config_file):
            logger.critical(config_file + " not found!")
            return

        with open(config_file, 'r') as f:
            self.maps = json.load(f)

        for key in ("data_path", "result_path", "cache_path"):
            if key not in self.maps:
                raise Exception("Missing " + key + " in the json configuration file")

        self.data_path = self.maps["data_path"]
        self.result_path = self.maps["result_path"]
        self.cache_path = self.maps["cache_path"]

        # Every worker process runs this at start-up, so the directory may
        # appear between a check and the creation.
        os.makedirs(self.cache_path, exist_ok=True)

    @staticmethod
    def _ensure_dependencies():
        """Fail with a clear message when optional plotting dependencies are missing."""
        missing_dependencies = []

        if _NUMPY_IMPORT_ERROR is not None:
            missing_dependencies.append(f"numpy ({_NUMPY_IMPORT_ERROR})")

        if _PLOTTING_IMPORT_ERROR is not None:
            missing_dependencies.append("matplotlib/basemap")
        if _SHAPEFILE_IMPORT_ERROR is not None:
            missing_dependencies.append("pyshp")
        if _NETCDF_IMPORT_ERROR is not None:
            missing_dependencies.append("netCDF4")
        if _SCIPY_IMPORT_ERROR is not None:
            missing_dependencies.append("scipy")
        if _PLACES_IMPORT_ERROR is not None:
            missing_dependencies.append("core.Places dependencies")
        if _HAVERSINE_IMPORT_ERROR is not None:
            missing_dependencies.append("haversine")
        if _PIL_IMPORT_ERROR is not None:
            missing_dependencies.append("Pillow")

        if missing_dependencies:
            raise RuntimeError(
                "Plotter requires optional dependencies that are not installed: "
                + ", ".join(missing_dependencies)
            )

    def _load_cache_file(self, cache_file):
        """Return an unpickled cache entry, or None when it is absent or unreadable."""
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None
        except Exception as exc:
            # Entries left by an interrupted writer or by another library
            # version are rebuilt instead of failing the request.
            logger.warning("Discarding unreadable plot cache entry %s: %s", cache_file, exc)
            return None

    def _store_cache_file(self, cache_file, value):
        """Publish a cache entry atomically; the cache is an optimization only."""
        try:
            write_atomic(
                cache_file,
                lambda f: pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL),
                binary=True,
            )
        except OSError as exc:
            logger.warning("Unable to write plot cache entry %s: %s", cache_file, exc)

    @staticmethod
    def _basemap_matches(basemap, bounds):
        """Return whether a cached basemap was built for the requested bounds."""
        try:
            cached_bounds = (
                basemap.llcrnrlon, basemap.llcrnrlat, basemap.urcrnrlon, basemap.urcrnrlat
            )
            return bool(np.allclose(cached_bounds, bounds, rtol=0, atol=1e-9))
        except (AttributeError, TypeError, ValueError):
            return False

    def _get_place_map(self, place, min_lon, min_lat, max_lon, max_lat):
        """Return the cached projection state for the requested place bounds."""
        bounds = (float(min_lon), float(min_lat), float(max_lon), float(max_lat))

        place_map = self._place_maps.get(place)
        if place_map is not None and place_map.bounds == bounds:
            self._place_maps.move_to_end(place)
            return place_map

        basemap_key = os.path.join(self.cache_path, place + '.pkl')
        basemap = self._load_cache_file(basemap_key)
        # A place whose bounding box was edited keeps its identifier, so the
        # pickled projection has to be checked against the current bounds.
        if basemap is None or not self._basemap_matches(basemap, bounds):
            basemap = Basemap(
                projection='merc',
                llcrnrlon=bounds[0], llcrnrlat=bounds[1],
                urcrnrlon=bounds[2], urcrnrlat=bounds[3]
            )
            self._store_cache_file(basemap_key, basemap)

        place_map = _PlaceMap(basemap, bounds)
        self._place_maps[place] = place_map
        self._place_maps.move_to_end(place)
        while len(self._place_maps) > _PLACE_MAP_CACHE_SIZE:
            self._place_maps.popitem(last=False)
        return place_map

    # Kept for callers that only need the projection.
    def _get_basemap(self, place, min_lon, min_lat, max_lon, max_lat):
        """Return a cached basemap instance for the requested place bounds."""
        return self._get_place_map(place, min_lon, min_lat, max_lon, max_lat).basemap

    @staticmethod
    def _axis_window(axis, lower, upper, margin=_GRID_MARGIN):
        """Return the slice of a monotonic 1-D axis covering [lower, upper] plus a margin."""
        axis = np.asarray(axis)
        if axis.ndim != 1 or axis.shape[0] < 2:
            return slice(None)

        size = axis.shape[0]
        ascending = axis[0] <= axis[-1]
        ordered = axis if ascending else axis[::-1]
        start = max(int(np.searchsorted(ordered, lower, side="left")) - 1 - margin, 0)
        stop = min(int(np.searchsorted(ordered, upper, side="right")) + 1 + margin, size)
        if stop - start < 2:
            return slice(0, size)
        if not ascending:
            start, stop = size - stop, size - start
        return slice(start, stop)

    def _read_variable(self, nc, variable_name, time_index=None, level_index=None, window=None):
        """Read only the requested slice from a NetCDF variable.

        ``window`` is a ``(lat_slice, lon_slice)`` pair applied to the two
        trailing dimensions, so only the cells around the place are read.
        """
        if variable_name is None or variable_name == "":
            return None

        variable = nc.variables[variable_name]
        leading = tuple(index for index in (time_index, level_index) if index is not None)
        if window is not None:
            return variable[leading + (Ellipsis,) + tuple(window)]
        if len(leading) == 2:
            return variable[leading]
        if leading:
            return variable[leading[0]]
        return variable[:]

    def _get_localized_value(self, values, language, default=""):
        """Return the best localized string available for the requested language."""
        if not isinstance(values, dict) or not values:
            return default

        if language in values:
            return values[language]

        language_prefix = (language or "").split("-", 1)[0]
        if language_prefix in values:
            return values[language_prefix]

        for key, value in values.items():
            if key.split("-", 1)[0] == language_prefix:
                return value

        return next(iter(values.values()), default)

    def _interpolate_scalar_grid(self, lons, lats, data, factor=1.0, max_points=350):
        """Densify a regular scalar grid to improve shaded and contour rendering quality."""
        if factor is None or factor <= 1:
            return lons, lats, data

        scalar_data = np.ma.asarray(data)
        if scalar_data.ndim != 2 or lons.shape != scalar_data.shape or lats.shape != scalar_data.shape:
            return lons, lats, data

        if min(scalar_data.shape) < 2:
            return lons, lats, data

        if np.ma.is_masked(scalar_data) and np.ma.getmaskarray(scalar_data).any():
            return lons, lats, data

        scalar_values = np.asarray(scalar_data, dtype=float)
        if not np.isfinite(scalar_values).all():
            return lons, lats, data

        # max_points caps how far an axis may grow; an axis that is already
        # denser than the cap is left alone rather than resampled down.
        rows, cols = scalar_values.shape
        target_rows = max(rows, min(max_points, int(round(rows * factor))))
        target_cols = max(cols, min(max_points, int(round(cols * factor))))

        if target_rows <= rows and target_cols <= cols:
            return lons, lats, data

        if scipy_zoom is not None:
            zoom_factors = (target_rows / rows, target_cols / cols)
            interpolation_order = 3 if min(rows, cols, target_rows, target_cols) >= 4 else 1
            dense_values = scipy_zoom(
                scalar_values,
                zoom_factors,
                order=interpolation_order,
                mode="nearest",
                prefilter=interpolation_order > 1,
            )
        else:
            # Keep basic grid densification available when SciPy is not
            # installed (for example in lightweight API/test environments).
            source_cols = np.arange(cols, dtype=float)
            target_col_axis = np.linspace(0, cols - 1, target_cols)
            horizontally_dense = np.vstack(
                [np.interp(target_col_axis, source_cols, row) for row in scalar_values]
            )
            source_rows = np.arange(rows, dtype=float)
            target_row_axis = np.linspace(0, rows - 1, target_rows)
            dense_values = np.column_stack(
                [np.interp(target_row_axis, source_rows, column) for column in horizontally_dense.T]
            )

        lon_axis = np.asarray(lons[0], dtype=float)
        lat_axis = np.asarray(lats[:, 0], dtype=float)
        dense_lon_axis = np.linspace(lon_axis[0], lon_axis[-1], target_cols)
        dense_lat_axis = np.linspace(lat_axis[0], lat_axis[-1], target_rows)
        dense_lons, dense_lats = np.meshgrid(dense_lon_axis, dense_lat_axis)

        return dense_lons, dense_lats, dense_values

    # Add a shaded layer to the basemap
    def _add_shaded(self, basemap, ax, values, lons, lats, data, colors, legend_title, position_legend, size="2%",pad="5%", label_size=8, ticks_position="right", draw_colorbars = True):
        """Internal helper for add shaded."""

        # Convert the colormap from 0-255 RGBA to 0.0-1.0 RGBA
        colors = [[j / 255 for j in i] for i in colors]

        # Append
        bounds = np.append(values[1:], values[-1] + 1)

        # Create a colormap with the listed colors skipping the first one
        cmap = ListedColormap(colors[1:])

        # Set the first color as the one below the bounds
        cmap.set_under(colors[0])

        # Set the last color as the ono over the bounds
        cmap.set_over(colors[-1])

        # Normalize the colormap on the bounds
        norm = BoundaryNorm(bounds, ncolors=len(colors) - 1)

        # Add a filled contour to the basemap
        cf = basemap.contourf(lons, lats, data, values[1:], cmap=cmap, norm=norm, latlon=True, extend='both',
                              vmin=values[0], vmax=values[-1], ax=ax)

        # Check if the color bars must be drawn
        if draw_colorbars:

            # Add the colorbar
            cf = basemap.colorbar(
                cf, position_legend, size=size, pad=pad, ticks=values[1:], fig=ax.get_figure(), ax=ax
            )

            # Set the tick parameters
            cf.ax.tick_params(labelsize=label_size)

            # Set the ticks position on the y axis
            cf.ax.yaxis.set_ticks_position(ticks_position)

            # Set the label position on the y axis
            cf.ax.yaxis.set_label_position(ticks_position)

            # Set the legend title
            cf.set_label(legend_title)

    @staticmethod
    def _read_shapefile(basemap, shapefile_path, bounds):
        """Return the projected parts of a shapefile that can fall inside the map."""
        min_lon, min_lat, max_lon, max_lat = bounds
        point_lons = []
        point_lats = []
        rings = []

        with pyshp.Reader(shapefile_path) as reader:
            for shape in reader.iterShapes():
                points = shape.points
                if not points:
                    continue

                if shape.shapeType in _POINT_SHAPE_TYPES:
                    for point in points:
                        if min_lon <= point[0] <= max_lon and min_lat <= point[1] <= max_lat:
                            point_lons.append(point[0])
                            point_lats.append(point[1])
                    continue

                box = shape.bbox
                if box[0] > max_lon or box[2] < min_lon or box[1] > max_lat or box[3] < min_lat:
                    continue

                # A record can hold far-apart parts (a country and its
                # islands), so each part is tested against the map as well.
                offsets = list(shape.parts) + [len(points)]
                for first, last in zip(offsets[:-1], offsets[1:]):
                    part = np.asarray(points[first:last], dtype=float)[:, :2]
                    if part.shape[0] < 2:
                        continue
                    part_lons = part[:, 0]
                    part_lats = part[:, 1]
                    if (
                        part_lons.min() > max_lon or part_lons.max() < min_lon
                        or part_lats.min() > max_lat or part_lats.max() < min_lat
                    ):
                        continue
                    x, y = basemap(part_lons, part_lats)
                    rings.append(np.column_stack((x, y)))

        # Projected one by one: the projection layer treats a one-element
        # array as a scalar, which newer NumPy releases reject.
        marker_points = np.array(
            [basemap(point_lon, point_lat) for point_lon, point_lat in zip(point_lons, point_lats)],
            dtype=float,
        ).reshape(-1, 2)

        return {"points": marker_points, "rings": rings}

    def _get_shapefile_geometry(self, place, place_map, shapefile_path):
        """Return cached projected shapefile geometry clipped to the place bounds."""
        try:
            stat = os.stat(shapefile_path + ".shp")
        except OSError:
            return None

        # Reading and projecting a continental shapefile dominates the cost of
        # a plot, while only a few of its parts intersect a place. The clipped
        # geometry is therefore kept per place, in memory and on disk.
        signature = (os.path.abspath(shapefile_path), stat.st_mtime_ns, stat.st_size) + place_map.bounds
        geometry = place_map.shapes.get(shapefile_path)
        if geometry is not None and geometry.get("signature") == signature:
            return geometry

        cache_file = os.path.join(
            self.cache_path, place + "." + os.path.basename(shapefile_path) + ".shp.pkl"
        )
        geometry = self._load_cache_file(cache_file)
        if not isinstance(geometry, dict) or geometry.get("signature") != signature:
            geometry = self._read_shapefile(place_map.basemap, shapefile_path, place_map.bounds)
            geometry["signature"] = signature
            self._store_cache_file(cache_file, geometry)

        place_map.shapes[shapefile_path] = geometry
        return geometry

    # Add a shapefiles layer to the basemap
    def _add_shapefiles(self, ax, place, place_map, shapefiles):
        """Draw point, outline and filled shapefiles on the map axes."""
        for shapefile in shapefiles:
            shapefile_path = shapefile.get("path")
            if not shapefile_path:
                continue

            geometry = self._get_shapefile_geometry(place, place_map, shapefile_path)
            if geometry is None:
                continue

            shapefile_color = shapefile.get("color", "black")

            # Point shapefiles are drawn only when a marker is configured.
            marker = shapefile.get("marker")
            marker_points = geometry["points"]
            if marker is not None and len(marker_points):
                ax.plot(
                    marker_points[:, 0], marker_points[:, 1], linestyle="None",
                    marker=marker.get("symbol", "+"), color=shapefile_color,
                    markersize=marker.get("marker_size", marker.get("size", 1)),
                    markeredgewidth=marker.get("edge_width", 1)
                )

            rings = geometry["rings"]
            if not rings:
                continue

            if "fillcolor" in shapefile:
                ax.add_collection(
                    PolyCollection(
                        rings, closed=True, facecolor=shapefile["fillcolor"],
                        edgecolor=shapefile_color, linewidths=0.5
                    ),
                    autolim=False
                )
            else:
                ax.add_collection(
                    LineCollection(rings, colors=shapefile_color, linewidths=0.5, antialiaseds=(1,)),
                    autolim=False
                )

    def _load_watermark(self, watermark_path):
        """Return the decoded watermark image, reusing it across renders."""
        logo = self._watermark_image_cache.get(watermark_path)
        if logo is None:
            with Image.open(watermark_path) as source:
                logo = source.convert("RGBA")
            self._watermark_image_cache[watermark_path] = logo
        return logo

    def _add_watermark(self, plot_png, watermarks):
        """Return the PNG payload of a rendered plot with the watermarks pasted on."""
        plot_image = Image.open(io.BytesIO(plot_png)).convert("RGBA")
        resample_filter = getattr(Image, "Resampling", Image).LANCZOS

        for watermark in watermarks:
            watermark_path = watermark.get("path")
            if not watermark_path or not os.path.exists(watermark_path):
                logger.warning("Skipping missing watermark asset: %s", watermark_path)
                continue

            # resize() returns a new image, so the cached logo is never altered.
            logo = self._load_watermark(watermark_path)
            logo_width = max(1, int(plot_image.width * watermark.get('dim', 0.15)))
            logo = logo.resize((logo_width, max(1, int(logo_width * (logo.height / logo.width)))), resample_filter)

            alpha = ImageEnhance.Brightness(logo.getchannel("A")).enhance(watermark.get('opacity', 1))
            logo.putalpha(alpha)

            positions = {
                "top-right": (plot_image.width - logo.width - 40, 60),
                "top-left": (40, 50),
                "bottom-right": (plot_image.width - logo.width - 40, plot_image.height - logo.height - 60),
                "bottom-left": (40, plot_image.height - logo.height - 60)
            }

            logo_position = positions.get(watermark.get('position'), positions["top-right"])

            plot_image.paste(logo, logo_position, logo)

        output = io.BytesIO()
        plot_image.save(output, format="PNG")
        return output.getvalue()

    def _resolve_plot(self, prod, output):
        """Return the product map and the output definition, validating the configuration."""
        if self.maps is None:
            raise PlotConfigurationError("The maps configuration file is not loaded")

        product_maps = self.maps.get("products")
        if product_maps is None:
            raise PlotConfigurationError("The products key missing in the configuration file")
        if prod not in product_maps:
            raise PlotConfigurationError("The " + prod + " key is missing in the products definition")
        product_map = product_maps[prod]

        if "outputs" not in product_map:
            raise PlotConfigurationError("The outputs key is missing in products."+prod)
        outputs = product_map["outputs"]
        if output not in outputs:
            raise PlotConfigurationError("The " + output + " key is missing in products."+prod+".outputs")
        outputs_output = outputs[output]
        if "plot" not in outputs_output:
            raise PlotConfigurationError("The plot key is missing in products."+prod+".outputs." + output)
        if "layers" not in outputs_output["plot"]:
            raise PlotConfigurationError("The layers key is not present in products."+prod+".outputs." + output+".plot")

        for layer in outputs_output["plot"]["layers"]:
            colormap_name = layer.get("colormap")
            if colormap_name and colormap_name not in self.maps.get("colormaps", {}):
                raise PlotConfigurationError("The " + colormap_name + " is not present in the configuration json file")

        return product_map, outputs_output

    @staticmethod
    def _resolve_tuning(product_map, domain_id, diag):
        """Return the symbol-density settings matching the place diagonal in km."""
        tuning = {"skip": 20, "scale": 1, "hpa_tick": 1, "barb_length": 1}

        for item in product_map.get("config", {}).get(domain_id, []):
            if "ge" in item and item["ge"] <= diag and ("lt" not in item or diag < item["lt"]):
                values = item.get("values", {})
                for key in tuning:
                    if key in values:
                        tuning[key] = values[key]
                break

        if int(tuning["skip"]) < 1:
            raise PlotConfigurationError("The skip value must be a positive integer")
        tuning["skip"] = int(tuning["skip"])
        return tuning

    def render(self, place, prod, output, dateTime, language="en-US", draw_colorbars=True):
        """Render one plot image and return its relative path and file name."""
        place_info = self.places.get_place_by_id(place)
        if (
            place_info is None
            or (
                str((place_info.get('long_name') or {}).get('it')) == "Italia"
                and prod in {"rms3", "aiq3", "wcm3"}
            )
        ):
            relative_path = self.config['NOIMAGE_PATH']
            image_name = "noimage.png"
            return relative_path, image_name

        # Reject unknown products and outputs before touching the archive.
        product_map, outputs_output = self._resolve_plot(prod, output)

        minLat = place_info["minLat"]
        maxLat = place_info["maxLat"]
        minLon = place_info["minLon"]
        maxLon = place_info["maxLon"]

        diag = haversine.haversine((minLat, minLon), (maxLat, maxLon))
        domain = self.places.get_domain_and_indeces_by_product_and_place(prod, place, dateTime)
        if domain is None:
            raise DataNotAvailableException(prod + " is not available for " + place)
        domainId = domain[0]

        year = dateTime[:4]
        month = dateTime[4:6]
        day = dateTime[6:8]
        hour = dateTime[9:11]
        minute = dateTime[11:13]
        timestamp = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))

        data_file = self.data_path + \
            prod + os.path.sep + domainId + os.path.sep +"archive" + \
            os.path.sep + year + os.path.sep  + month + os.path.sep + \
            day + os.path.sep  + prod + "_" + domainId + "_" + dateTime + ".nc"

        if os.path.exists(data_file) is False:
            logger.error('data_file : ' + str(data_file))
            raise DataNotAvailableException(data_file)

        relative_path = "plt" + os.path.sep + place + os.path.sep + prod + os.path.sep + year + os.path.sep + month + os.path.sep + day
        image_name = "plt_" + place + "_" + prod + "_" + dateTime + "_" + output + "_1024x768.png"
        result_file = self.result_path + os.path.sep + relative_path + os.path.sep + image_name
        os.makedirs(os.path.dirname(result_file), exist_ok=True)

        tuning = self._resolve_tuning(product_map, domainId, diag)
        place_name = self._get_localized_value(place_info.get("name"), language, place)
        plot_title_template = self._get_localized_value(self.maps.get("title"), language, "__name__")
        plot_title = timestamp.strftime(plot_title_template).replace("__name__", place_name)

        with _RENDER_LOCK:
            plot_png = self._render_png(
                place, (minLon, minLat, maxLon, maxLat), data_file, outputs_output["plot"]["layers"],
                tuning, output, plot_title, language, draw_colorbars
            )

        # Readers (this API and the web server publishing the images) must
        # never observe a partially written PNG.
        write_atomic(result_file, lambda f: f.write(plot_png), binary=True)

        return relative_path, image_name

    def _render_png(self, place, bounds, data_file, layers, tuning, output, plot_title, language, draw_colorbars):
        """Draw every layer of a plot and return the encoded PNG payload."""
        minLon, minLat, maxLon, maxLat = bounds
        skip = tuning["skip"]
        scale = tuning["scale"]
        barb_length = tuning["barb_length"]
        # The wn2 direction-change isolines use a fixed coarse interval.
        contour_step = 140 if output == 'wn2' else tuning["hpa_tick"]

        nc = None
        fig = None
        try:
            nc = NetCDFFile(data_file)
            lat = np.asarray(nc.variables['latitude'][:], dtype=float)
            lon = np.asarray(nc.variables['longitude'][:], dtype=float)

            # Only the cells around the place are read and drawn: the archive
            # grids cover a whole model domain, the map a single place.
            lat_window = self._axis_window(lat, minLat, maxLat, _GRID_MARGIN + skip)
            lon_window = self._axis_window(lon, minLon, maxLon, _GRID_MARGIN + skip)
            window = (lat_window, lon_window)
            lons, lats = np.meshgrid(lon[lon_window], lat[lat_window])

            # Wind symbols are thinned on the lattice of the full grid, so the
            # same cells are picked whatever window the place selects.
            skip2 = (
                slice(-(lat_window.start or 0) % skip, None, skip),
                slice(-(lon_window.start or 0) % skip, None, skip),
            )

            place_map = self._get_place_map(place, minLon, minLat, maxLon, maxLat)
            basemap = place_map.basemap
            fig = plt.figure()
            ax = fig.add_subplot(111)
            basemap.set_axes_limits(ax=ax)

            if "shapefiles" in self.maps:
                self._add_shapefiles(ax, place, place_map, self.maps["shapefiles"])

            lat_step = max((maxLat - minLat) / 4, 0.1)
            lon_step = max((maxLon - minLon) / 4, 0.1)
            parallels = np.arange(minLat, maxLat, lat_step)
            meridians = np.arange(minLon, maxLon, lon_step)
            basemap.drawparallels(parallels, labels=[1, 0, 0, 0], fontsize=4, linewidth=0.1, ax=ax)
            basemap.drawmeridians(meridians, labels=[0, 0, 0, 1], fontsize=4, linewidth=0.1, ax=ax)

            ax.set_title(plot_title)

            watermarks = []

            for layer in layers:
                time = layer.get("time")
                level = layer.get("level")
                layer_type = layer.get("type", "contourf")
                text = self._get_localized_value(layer.get("text"), language, "")
                pad = layer.get("pad", "10%")
                position = layer.get("position", "left")
                ticks_position = layer.get("ticks_position", "left")
                label_size = layer.get("label_size", 8)
                colormap_name = layer.get("colormap")
                colormap = self.maps["colormaps"][colormap_name] if colormap_name else None
                clevs = None
                clev_min = layer.get("clev_min", 0)
                clev_max = layer.get("clev_max", 100)
                colors = layer.get("colors")
                interpolation_factor = layer.get("interpolation_factor", 2.0)
                interpolation_max_points = layer.get("interpolation_max_points", 350)

                var1 = self._read_variable(nc, layer.get("var1"), time, level, window)
                var2 = self._read_variable(nc, layer.get("var2"), time, level, window)

                if "a" in layer:
                    if var1 is not None:
                        var1 = var1 * layer["a"]
                    if var2 is not None:
                        var2 = var2 * layer["a"]

                if "b" in layer:
                    if var1 is not None:
                        var1 = var1 + layer["b"]
                    if var2 is not None:
                        var2 = var2 + layer["b"]

                if colormap is not None and "clevs" in colormap and "ccols" in colormap:
                    clevs = colormap["clevs"]
                    colors = [tuple(x) for x in colormap["ccols"]]

                if "shaded" in layer_type:
                    if colors is None or clevs is None:
                        raise PlotConfigurationError("Shaded layers require colormap-derived clevs and colors")
                    var = np.hypot(var1, var2) if var2 is not None else var1
                    interp_lons, interp_lats, interp_var = self._interpolate_scalar_grid(
                        lons, lats, var, interpolation_factor, interpolation_max_points
                    )
                    self._add_shaded(
                        basemap, ax, clevs, interp_lons, interp_lats, interp_var, colors, text, position,
                        pad=pad, ticks_position=ticks_position, label_size=label_size,
                        draw_colorbars=draw_colorbars
                    )
                elif "contour" in layer_type:
                    if contour_step <= 0:
                        raise PlotConfigurationError("The hpa_tick value must be positive")
                    var = np.hypot(var1, var2) if var2 is not None else var1
                    interp_lons, interp_lats, interp_var = self._interpolate_scalar_grid(
                        lons, lats, var, interpolation_factor, interpolation_max_points
                    )
                    clevs = np.arange(clev_min, clev_max, contour_step)
                    cs = basemap.contour(
                        interp_lons, interp_lats, interp_var, clevs, colors=colors,
                        linewidths=0.5, latlon=True, ax=ax
                    )
                    clabels = ax.clabel(cs, fontsize=6, inline=1, fmt='%1.0f')
                    for txt in clabels:
                        txt.set_bbox(dict(facecolor='white', edgecolor='none', pad=0))
                elif "angle" in layer_type:
                    # Compass bearing to mathematical angle; cos/sin make any
                    # wrap-around normalization unnecessary.
                    var = np.deg2rad(90 - var1[skip2])
                    basemap.quiver(
                        lons[skip2], lats[skip2], np.cos(var), np.sin(var),
                        latlon=True, scale=scale, scale_units="inches",
                        pivot='middle', linewidths=.01, edgecolors='gray', ax=ax
                    )
                elif "versor" in layer_type:
                    var = np.hypot(var1[skip2], var2[skip2])
                    safe_var1 = np.divide(var1[skip2], var, out=np.zeros_like(var1[skip2], dtype=float), where=var != 0)
                    safe_var2 = np.divide(var2[skip2], var, out=np.zeros_like(var2[skip2], dtype=float), where=var != 0)
                    basemap.quiver(
                        lons[skip2], lats[skip2],
                        safe_var1, safe_var2,
                        latlon=True, scale=scale, scale_units="inches",
                        pivot='middle', linewidths=.01, edgecolors='gray', ax=ax
                    )
                elif "vector" in layer_type:
                    basemap.quiver(
                        lons[skip2], lats[skip2], var1[skip2], var2[skip2],
                        latlon=True, scale=scale, scale_units="inches", pivot='middle', ax=ax
                    )
                elif "barbs" in layer_type:
                    basemap.barbs(
                        lons[skip2], lats[skip2], var1[skip2], var2[skip2],
                        latlon=True, pivot='middle', barbcolor='#666666',
                        length=barb_length, linewidths=0.3, ax=ax
                    )
                elif "shapefiles" in layer_type:
                    if "shapefiles" in layer:
                        self._add_shapefiles(ax, place, place_map, layer["shapefiles"])
                elif "watermark" in layer_type:
                    watermarks.extend(layer.get("watermarks", []))

            buffer = io.BytesIO()
            if watermarks:
                # This PNG is decoded again right away, so favour speed over size.
                fig.savefig(buffer, dpi=300, bbox_inches='tight', format='png', pil_kwargs={"compress_level": 1})
                return self._add_watermark(buffer.getvalue(), watermarks)

            fig.savefig(buffer, dpi=300, bbox_inches='tight', format='png')
            return buffer.getvalue()
        finally:
            if nc is not None:
                nc.close()
            if fig is not None:
                plt.close(fig)
