"""Application-facing endpoints for tiled payload services."""

from flask_restx import Namespace, Resource
from flask import jsonify, request

from core.GetParams import get_params
from core.MemcachedMethodHandlers import get_resource, set_resource
import json
import app

api = Namespace('apps', description='Application-facing integration endpoints and tiled payload services.')


# @api.route('/test/cache')
# class TestCache(Resource):
#    def get(self):
#        set_resource(request, "ciao", app.cache, app.use_pymemcache)
#        out = get_resource(request, app.cache, app.use_pymemcache)
#        return str(out)


# @api.route('/test/database')
# class TestDB(Resource):
#    def get(self):
#        client = pymongo.MongoClient()
#        db = client['ccmmma-database']
#        places = db['places']
#        data = places.find({})
#        for item in data:
#            print(item)


# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE
@api.route('/owm/<string:prod>/<string:placeprefix>/<int:z>/<int:x>/<int:y>.geojson', methods=['GET', 'OPTIONS'])
class AppsOwmWeatherProdPlacePrefix(Resource):
    """Resource handler for apps owm weather prod place prefix operations."""
    @api.doc(
        summary="Get application weather tile data",
        params={
            "prod": "Forecast product code",
            "placeprefix": "Place prefix filter used to constrain the response",
            "z": "Tile zoom level",
            "x": "Tile x coordinate",
            "y": "Tile y coordinate"
        },
        responses={200: "GeoJSON-style payload returned successfully", 400: "Unsupported request"}
    )
    def get(self, prod, placeprefix, z, x, y):
        """
        Return an application-oriented weather tile payload for the requested product and tile coordinates.

        Example:
        `GET /apps/owm/wrf5/prov/10/552/384.geojson`
        """

        if placeprefix == "reg":
            return {'message': 'The place \'reg\' is not used'}

        res = get_resource(request, app.cache, app.use_pymemcache)

        # Check Memcache
        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            if res is None:
        
                params = get_params({'date': None})
                res = app.tiles.get_weather_ex(prod, placeprefix, params, z, x, y)

                # Save on Diskcache
                app.diskcache.set(request, res, 'json', app.use_disk_cached)

            # Promote disk hits as well as freshly generated tiles. Without this,
            # every request after a memcache eviction repeated disk I/O and JSON
            # decoding for the full GeoJSON document.
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = json.loads(res)
        return jsonify(res)
