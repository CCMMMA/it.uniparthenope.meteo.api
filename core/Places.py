"""Place lookup services used by the public API endpoints."""

import json
import os
import netCDF4
import numpy as np
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
from core.MongoDbHandlers import MongoDBHandlers
from core.Logger import logger

try:
    from numpy.compat import basestring
except ImportError:
    basestring = str

class Places(object):
    """Service or helper that encapsulates places behavior."""
    config = {}
    proj = {"_id": 0, "id": 1, "name": 1, "long_name": 1, "pos": 1, "bbox": 1, "country": 1}

    def __init__(self, cfg):
        """Initialize places state."""
        self.config = cfg
        self.mongo = MongoDBHandlers(self.config)
        self._domain_grid_cache = {}

    @staticmethod
    def _normalize_filter(filter_value):
        """Return a normalized filter list for MongoDB prefix queries."""
        if filter_value is None:
            return None
        if isinstance(filter_value, str) and "[" in filter_value:
            tmp = json.loads("{ \"filter\": " + filter_value + "}")
            return tmp['filter']
        return filter_value

    def _archive_path(self, product, domain, ncep_date):
        """Return the NetCDF archive path for a product/domain/date tuple."""
        return os.path.join(
            self.config['BASE_PATH'],
            product,
            domain,
            self.config.get('ARCHIVE', 'archive'),
            ncep_date[0:4],
            ncep_date[4:6],
            ncep_date[6:8],
            f"{product}_{domain}_{ncep_date}.nc",
        )

    def _get_domain_grid(self, product, domain, ncep_date):
        """Return cached grid metadata for one product/domain/date tuple."""
        cache_key = (product, domain, ncep_date)
        cached = self._domain_grid_cache.get(cache_key)
        if cached is not None:
            return cached

        url = self._archive_path(product, domain, ncep_date)
        with netCDF4.Dataset(url) as dataset:
            longitudes = dataset.variables["longitude"][:]
            latitudes = dataset.variables["latitude"][:]
            ipoints = len(longitudes)
            jpoints = len(latitudes)
            lon0 = float(longitudes[0])
            lat0 = float(latitudes[0])
            lon1 = float(longitudes[-1])
            lat1 = float(latitudes[-1])
            dxll = (lon1 - lon0) / ipoints
            dyll = (lat1 - lat0) / jpoints

        cached = {
            "ipoints": ipoints,
            "jpoints": jpoints,
            "lon0": lon0,
            "lat0": lat0,
            "lon1": lon1,
            "lat1": lat1,
            "dxll": dxll,
            "dyll": dyll,
        }
        self._domain_grid_cache[cache_key] = cached
        return cached

    @staticmethod
    def is_in_bb(lon_min, lat_min, lon_max, lat_max, lon, lat):
        """Return whether in bb."""
        if lon_min <= lon <= lon_max:
            if lat_min <= lat <= lat_max:
                return True
        return False

    @staticmethod
    def haversine_np(lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)

        All args must be of equal length.

        """
        lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

        d_lon = lon2 - lon1
        d_lat = lat2 - lat1

        a = np.sin(d_lat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(d_lon / 2.0) ** 2

        c = 2 * np.arcsin(np.sqrt(a))
        km = 6367 * c
        return km

    @staticmethod
    def haversine(lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))

        # 6367 km is the radius of the Earth
        km = 6367 * c
        return km
    
    
    def get_all_places(self, place):
        """Return all places."""
        return self.mongo.get_query(place, all_places=True)

    def get_domain_and_indeces_by_product_and_place(self, product, place_id, date=None):
        """Return domain and indeces by product and place."""
        # conn = pymongo.MongoClient()
        # db = conn[self.config['DATABASE']]  # connessione databse
        # places = db['places']  # richiesta collezione 'places'
        query = {"id": place_id, "prods." + product: {"$exists": True}}
        proj = {"_id": 0, "minLon": 1, "minLat": 1, "maxLon": 1, "maxLat": 1, "prods." + product: 1}
        result = self.mongo.get_query_find_one('places', query, proj)

        if result is not None and product in result['prods'] and result['prods'] != {}:
            res = 999
            domain = None
            for d in result['prods'][product]:
                if result['prods'][product][d]['res'] < res:
                    res = result['prods'][product][d]['res']
                    domain = d

            if domain is None:
                return None

            if product in {"wrf5", "rms3", "wcm3", "ww33", "aiq3"}:
                if date is None:
                    nowutc_datetime = datetime.utcnow()
                    ncep_date = nowutc_datetime.strftime("%Y%m%dZ%H00")
                else:
                    ncep_date = date

                grid = self._get_domain_grid(product, domain, ncep_date)

                minLon = float(result['minLon'])
                minLat = float(result['minLat'])
                maxLon = float(result['maxLon'])
                maxLat = float(result['maxLat'])

                minLon = max(minLon, grid["lon0"])
                maxLon = min(maxLon, grid["lon1"])
                minLat = max(minLat, grid["lat0"])
                maxLat = min(maxLat, grid["lat1"])

                Imin = max(0, int((minLon - grid["lon0"]) / grid["dxll"]))
                Imax = min(grid["ipoints"] - 1, int((maxLon - grid["lon0"]) / grid["dxll"]))
                Jmin = max(0, int((minLat - grid["lat0"]) / grid["dyll"]))
                Jmax = min(grid["jpoints"] - 1, int((maxLat - grid["lat0"]) / grid["dyll"]))

                return domain, Jmin, Jmax, Imin, Imax

            elif "Jmin" in result['prods'][product][domain] and "Jmax" in result['prods'][product][domain] and "Imin" in result['prods'][product][domain] and "Imax" in result['prods'][product][domain]:
                Jmin = result["prods"][product][domain]["Jmin"]
                Jmax = result["prods"][product][domain]["Jmax"]
                Imin = result["prods"][product][domain]["Imin"]
                Imax = result["prods"][product][domain]["Imax"]
                # print(domain)
                # print(Jmin)
                # print(Jmax)
                # print(Imin)
                # print(Imax)
                return domain, Jmin, Jmax, Imin, Imax

        return None

    def get_places_by_bb(self, lon_min, lat_min, lon_max, lat_max, options=None):
        """Return places by bb."""
        # result = []
        # conn = pymongo.MongoClient()
        # db = conn[self.config['DATABASE']]
        # places = db['places']
        filter = None
        diag = None
        zoom = None

        if options is not None:
            try:
                if 'filter' in options and options['filter'] is not None:
                    filter = options['filter']
            except:
                pass

            try:
                if 'diag' in options and options['diag'] is not None:
                    diag = options['diag']
            except:
                pass
            try:
                if 'zoom' in options and options['zoom'] is not None:
                    zoom = options['zoom']
            except:
                pass

        filter = self._normalize_filter(filter)

        query = {
            "$and": [
                {"loc": {
                    "$geoWithin": {
                        "$polygon": [
                            [lon_min, lat_min], [lon_min, lat_max],
                            [lon_max, lat_max], [lon_max, lat_min]
                        ]
                    }
                }}
            ]
        }
        if filter is not None:
            ff = []
            for f in filter:
                ff.append({"id": {'$regex': f + '.*'}})
            query["$and"].append({"$or": ff})

        if diag is not None:
            query["$and"].append({"diag": {"$gte": diag['min'], "$lte": diag['max']}})

        if zoom is not None:
            query["$and"].append({"zoom.min": {"$lte": zoom}})
            query["$and"].append({"zoom.max": {"$gte": zoom}})

        # print(query)

        # print "Query:"+str(query)
        # items = places.find(query, self.proj)
        # for item in items:
        #    print(item)
        # for item in items:
        #    result.append(item)
        # conn.close()
        # return  result
        return self.mongo.get_query('places', query, self.proj)

    def get_places_by_ll(self, lon, lat, options=None):
        """Return places by ll."""
        range = -1
        filter = ""
        prod = ""
        limit = 9

        if options is not None:
            if "filter" in options and options['filter'] is not None:
                filter = options['filter']
            if "range" in options and options['range'] is not None:
                range = float(options['range'])
            if "prod" in options and options['prod'] is not None:
                prod = options['prod']
            if "limit" in options and options['limit'] is not None:
                limit = int(options['limit'])

        # conn = pymongo.MongoClient()
        # db = conn[self.config['DATABASE']]
        # places = db['places']
        query = {
            "pos": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "$minDistance": 0
                }
            }
        }
        if range > 0:
            query['pos']['$near']['maxDistance'] = range

        if filter != "":
            query = {"$and": [query, {"id": {'$regex': filter + '.*'}}]}

        # items = places.find(query, self.proj).limit(limit)
        # return self.mongo.get_query('places', query, self.proj, limit=limit)
        items = self.mongo.get_query_find_one('places', query, self.proj)
        return items
 

    def get_place_by_id(self, id, options=None):
        """Return place by id."""
        # conn = pymongo.MongoClient()
        # db = conn[self.config['DATABASE']]
        # places = db['places']
        query = {"id": id}
        if options is not None:
            if "prod" in options and options['prod'] is not None:
                prod = options['prod']
                query["prods." + prod] = {"$exists": True}
        # mongo_db = MongoDBHandlers(self.config)
        # result = mongo_db.get_query('place', query, {"_id": 0})
        # result = places.find_one(query, {"_id": 0})
        # return result
        return self.mongo.get_query_find_one('places', query, {"_id": 0})

    def get_places_by_name(self, name, options=None):
        """Return places by name."""
        filter = ""
        limit = 9

        if options is not None:
            if "filter" in options and options['filter'] is not None:
                filter = options['filter']
            if "limit" in options and options['limit'] is not None:
                limit = int(options['limit'])

        # conn = pymongo.MongoClient()
        # db = conn[self.config['DATABASE']]
        # places = db['places']
        query = {"$or": [{"long_name.en": {"$regex": str(name), "$options": 'i'}},
                         {"long_name.it": {"$regex": str(name), "$options": 'i'}}]}
        if filter != "":
            # print "--------->filter:"+str(filter)
            ff = []
            if isinstance(filter, basestring):
                ff = [{"id": {'$regex': filter + '.*'}}]
            elif all(isinstance(item, basestring) for item in filter):
                for item in filter:
                    ff.append({"id": {'$regex': item + '.*'}})
            else:
                pass

            query = {"$and": [query, {"$or": ff}]}

        # print str(query)
        # items = places.find(query, self.proj).limit(limit)
        # for item in items:
        #    result.append(item)
        # conn.close()
        return self.mongo.get_query('places', query, self.proj, limit=limit)


    def get_domain_by_product_and_ll(self, prod, lat, lon, options=None):
        """Return domain by product and ll."""
        domain = ""
        place = self.get_places_by_ll(lon, lat)
        logger.info(f"place : {place}")
        domain_indeces = self.get_domain_and_indeces_by_product_and_place(prod, place['id'])
        logger.info(f"domain_indeces : {domain_indeces}")
        if domain_indeces is not None:
            (domain, Jmin, Jmax, Imin, Imax) = domain_indeces
        return domain
        
"""
if __name__ == "__main__":
    fname = "../etc/ccmmmaapi.development.conf"
    config = {}
    with open(fname) as f:
        content = f.readlines()
        for line in content:
            line = line.replace("\n", "").replace("\r", "")
            if line == "" or line.startswith('#') or not " = " in line:
                continue

            parts = line.split(" = ")

            if '"' in parts[1][0] and '"' in parts[1][-1:]:
                config[parts[0]] = parts[1].replace('"', '')
            else:
                if '.' in parts[1]:
                    config[parts[0]] = float(parts[1])
                else:
                    config[parts[0]] = int(parts[1])
"""
# print
# str(config)
# places = Places(config)
# out = places.get_places_by_name("napoli")
# out=places.get_places_by_ll(14.14,40.85,options={"filter":"com"})
# print
# str(out)
