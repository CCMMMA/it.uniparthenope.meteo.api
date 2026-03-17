"""Tile-generation helpers for application-facing geospatial endpoints."""

import math
import datetime
from concurrent.futures import ThreadPoolExecutor
from geojson import Feature, FeatureCollection, Point
from core.Places import Places
import app


class Tiles(object):
    """Service or helper that encapsulates tiles behavior."""
    config = {}
    places = None

    def __init__(self, config):
        """Initialize tiles state."""
        self.config = config
        self.places = Places(config)

    def num(self, zoom):
        """Implement num for tiles."""
        return math.pow(2, zoom)

    def to_lon(self, x, zoom):
        """Implement to lon for tiles."""
        return x / self.num(zoom) * 360.0 - 180.0

    def to_bb(self, zoom, x, y):
        """Implement to bb for tiles."""
        result = {
            "lon_min": self.to_lon(x, zoom),
            "lon_max": self.to_lon(x + 1, zoom),
            "lat_max": self.to_lat(y, zoom),
            "lat_min": self.to_lat(y + 1, zoom)
        }
        return result

    def to_lat(self, y, zoom):
        """Implement to lat for tiles."""
        n = math.pi * (1 - 2 * y / self.num(zoom))
        return math.degrees(math.atan(math.sinh(n)))

     # funzione effettuata dal singolo thread
    def do_stuff(self, prod, params, item):
        """Implement do stuff for tiles."""
        feature = {}
        country = "it"
        place = item['id']
        dateTime = params["date"]

        if place.startswith("euro"):
            country = place[4:6]

        data = app.meteo_services.modelOutput({"prod": prod, "place": item["id"], "date": dateTime})

        if "ok" in data["result"]:
            cLon = item['pos']['coordinates'][0]
            cLat = item['pos']['coordinates'][1]
            feature = Feature(geometry=Point((cLon, cLat)))
            feature["properties"] = {"id": item['id'], "name": item['long_name']['it'], "country": country}

            for key in data.keys():
                feature["properties"][key] = data[key]

        return feature

    # prod : preso in input da url
    # placeprefix : preso in input da url
    # params : contiene la data esatta
    # z : preso in input da url
    # x : '' ''
    # y : '' ''
    def get_weather_ex(self, prod, placeprefix, params, z, x, y):
        """Return weather ex."""
        # setto la data esatta della chiamata
        if params['date'] is None:
            now = datetime.datetime.now()
            params['date'] = now.strftime("%Y%m%dZ%H00")

        # print "Date:"+str(params['date'])
        features = []

        # da coordinata x,y,z calcolo la min,max si long,lat
        bb = self.to_bb(z, x, y)

        # creo un filtro matematico
        filter = []
        for part in placeprefix.split("-"):
            filter.append(str(part))

        options = {
            "filter": filter,
            "zoom": z
        }

        # ricerco i luoghi con tali coordinate
        items = self.places.get_places_by_bb(bb['lon_min'], bb['lat_min'], bb['lon_max'], bb['lat_max'], options)

        max_workers = max(1, min(self.config['NUM_THREADS'], len(items))) if items else 1
        if items:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.do_stuff, prod, params, item) for item in items]
                features = [future.result() for future in futures]

        result = FeatureCollection(features)
        return result
