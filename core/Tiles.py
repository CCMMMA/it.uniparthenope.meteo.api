"""Tile-generation helpers for application-facing geospatial endpoints."""

import math
import datetime
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from geojson import Feature, FeatureCollection, Point
from core.Places import Places

# Deepest zoom served by the slippy-map clients; it also keeps 2**zoom small.
MAX_ZOOM = 22

# The prefix parts end up inside a MongoDB regular expression.
_PLACE_PREFIX_PART = re.compile(r"[A-Za-z0-9_]+")


class InvalidTileError(ValueError):
    """Exception raised when a tile address or place prefix cannot be served."""
    pass


class Tiles(object):
    """Build GeoJSON weather tiles from the places inside a slippy-map tile."""
    config = {}
    places = None

    def __init__(self, config, meteo_services):
        """Initialize tiles state."""
        self.config = config
        self.meteo_services = meteo_services
        self.places = Places(config)
        # Reuse workers across tile requests. Creating as many as NUM_THREADS for
        # every cache miss was particularly expensive for small, busy tiles and
        # allowed concurrent requests to create an unbounded number of threads.
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(self.config['NUM_THREADS'])),
            thread_name_prefix="weather-tile",
        )

    def num(self, zoom):
        """Return the number of tiles along one axis at the given zoom."""
        return math.pow(2, zoom)

    def to_lon(self, x, zoom):
        """Return the longitude of the western edge of tile column ``x``."""
        return x / self.num(zoom) * 360.0 - 180.0

    def to_bb(self, zoom, x, y):
        """Return the geographic bounding box of a tile."""
        result = {
            "lon_min": self.to_lon(x, zoom),
            "lon_max": self.to_lon(x + 1, zoom),
            "lat_max": self.to_lat(y, zoom),
            "lat_min": self.to_lat(y + 1, zoom)
        }
        return result

    def to_lat(self, y, zoom):
        """Return the latitude of the northern edge of tile row ``y``."""
        n = math.pi * (1 - 2 * y / self.num(zoom))
        return math.degrees(math.atan(math.sinh(n)))

    @staticmethod
    def _validate_tile(z, x, y):
        """Reject tile addresses outside the slippy-map grid."""
        if not 0 <= z <= MAX_ZOOM:
            raise InvalidTileError("Zoom level must be between 0 and " + str(MAX_ZOOM))
        size = 1 << z
        if not (0 <= x < size and 0 <= y < size):
            raise InvalidTileError("Tile coordinates are outside the grid of zoom level " + str(z))

    @staticmethod
    def _place_filter(placeprefix):
        """Return the place-id prefixes of a dash-separated request filter."""
        parts = str(placeprefix).split("-")
        for part in parts:
            # An empty or pattern-bearing part would match every place.
            if not _PLACE_PREFIX_PART.fullmatch(part):
                raise InvalidTileError("Invalid place prefix")
        return parts

     # funzione effettuata dal singolo thread
    def do_stuff(self, prod, params, item):
        """Return the feature of one place, or an empty dict when it has no data."""
        feature, _ = self._place_feature(prod, params, item)
        return feature

    def _place_feature(self, prod, params, item):
        """Return ``(feature, pending)`` for one place.

        ``pending`` is true when the place is known to the product but its
        forecast file is not readable yet, so the answer may change soon.
        """
        country = "it"
        place = item['id']
        dateTime = params["date"]

        if place.startswith("euro"):
            country = place[4:6]

        data = self.meteo_services.modelOutput(
            {"prod": prod, "place": item["id"], "date": dateTime}
        )

        result = data.get("result") or ""
        if "ok" not in result:
            return {}, data.get("details") == "Data not available"

        cLon = item['pos']['coordinates'][0]
        cLat = item['pos']['coordinates'][1]
        long_name = item.get('long_name') or {}
        feature = Feature(geometry=Point((cLon, cLat)))
        feature["properties"] = {
            "id": item['id'],
            "name": long_name.get('it', item['id']),
            "country": country
        }
        feature["properties"].update(data)

        return feature, False

    # prod : preso in input da url
    # placeprefix : preso in input da url
    # params : contiene la data esatta
    # z : preso in input da url
    # x : '' ''
    # y : '' ''
    def get_weather_ex(self, prod, placeprefix, params, z, x, y):
        """Return the weather tile as a GeoJSON feature collection."""
        return self.get_weather_tile(prod, placeprefix, params, z, x, y)[0]

    def get_weather_tile(self, prod, placeprefix, params, z, x, y):
        """Return ``(feature_collection, cacheable)`` for a weather tile.

        A tile is not cacheable while some of its places are still waiting for
        their forecast file: caching it would hide them until the entry expires.
        """
        self._validate_tile(z, x, y)

        options = {
            "filter": self._place_filter(placeprefix),
            "zoom": z
        }

        # setto la data esatta della chiamata; archive timestamps are UTC
        if params['date'] is None:
            now = datetime.datetime.now(datetime.timezone.utc)
            params['date'] = now.strftime("%Y%m%dZ%H00")

        features = []
        cacheable = True

        # da coordinata x,y,z calcolo la min,max si long,lat
        bb = self.to_bb(z, x, y)

        # ricerco i luoghi con tali coordinate
        items = self.places.get_places_by_bb(bb['lon_min'], bb['lat_min'], bb['lon_max'], bb['lat_max'], options)

        if items:
            worker = partial(self._place_feature, prod, params)
            # executor.map retains MongoDB result ordering. An unexpected
            # failure still aborts the tile, so a broken backend is reported
            # instead of being cached as an empty tile.
            for feature, pending in self._executor.map(worker, items):
                if feature:
                    features.append(feature)
                elif pending:
                    cacheable = False

        return FeatureCollection(features), cacheable
