from datetime import datetime
from flask_restx import Namespace, Resource
from flask import jsonify, request
from geojson import FeatureCollection

from core.GetParams import get_params
from core.Tiles import Tiles
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
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = json.loads(res)
        return jsonify(res)

'''
# TESTED AND WORKING -- OLD VERION 
@api.route('/owm/<string:prod>/<string:placeprefix>/<int:z>/<int:x>/<int:y>.geojson', methods=['GET', 'OPTIONS'])
class AppsOwmWeatherProdPlacePrefix(Resource):
    @api.doc()
    def get(self, prod, placeprefix, z, x, y):
        """
        :example: /apps/owm/wrf5/prov/10/552/384.geojson
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """

        if placeprefix == "reg":
            return {'message': 'The place \'reg\' is not used'}

        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({'date': None})
            res = app.tiles.get_weather_ex(prod, placeprefix, params, z, x, y)
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = json.loads(res)
        return jsonify(res)
'''

# TESTED AND WORKING -- NO CACHE USE 
@api.route('/sais/index')
class AppsSaisRisk(Resource):
    @api.doc(
        summary="Get SAIS index payload",
        responses={200: "SAIS index returned successfully", 503: "Source file unavailable"}
    )
    def get(self):
        """
        Return the SAIS index payload loaded from the configured JSON source.

        Example:
        `GET /apps/sais/index`
        """
        try:
            with open("/project/JsonData/sam3.json", "r") as file_sam3:
                data_json_string = file_sam3.read()
                file_sam3.close()
                data_object = json.loads(data_json_string)
                return jsonify({'sam3': data_object})
        except IOError as e:
            return jsonify({"details": "Service Unavailable", "result": "error", "e": str(e)}), 503


# @api.route('/sais/risk/ondameters')
# class AppsSaisRiskOndameters(Resource):
#    @api.doc()
#    def get(self):
#        """
#        :example: /apps/sais/risk/ondameters
#        :returns: json -- the return josn.
#        -------------------------------------------------------------------------------------------
#        """
#        try:
#            with open("/home/ccmmma/prometeo/models/SonOfBeach/output/sob.json", "r") as myfile:
#                data_json_string = myfile.read()
#                data_object = json.loads(data_json_string)
#                return jsonify({'ondameters': ['ondameters']})
#        except IOError as e:
#            return jsonify({"details": "Service Unavailable", "result": "error"})


# mi serve il file sob
# @api.route('/sais/risk/transects')
# class AppsSaisRiskTransects(Resource):
#    @api.doc()
#    def get(self):
#        """
#        :example: /apps/sais/risk/transects
#        :returns: json -- the return josn.
#        -------------------------------------------------------------------------------------------
#        """
#        try:
#            with open("/home/ccmmma/prometeo/models/SonOfBeach/output/sob.json", "r") as myfile:
#                data_json_string = myfile.read()
#                data_runup = json.loads(data_json_string)
#                return jsonify({'transects': data_runup['transects']})
#        except IOError as e:
#            return jsonify({"details": "Service Unavailable", "result": "error"})


# mi serve il file sob
# @api.route('sais/risk/transects/<string:tid>')
# class AppsSaisRiskTransectsById(Resource):
#    @api.doc()
#    def get(self, tid):
#        """
#        :example: /apps/sais/risk/transects/1
#        :returns: json -- the return josn.
#        -------------------------------------------------------------------------------------------
#        """
#        try:
#            with open("/home/montella/prometeo/SonOfBeach/output/sob.json", "r") as myfile:
#                data_json_tring = myfile.read()
#                data_runup = json.loads(data_json_tring)
#                result = []
#                for transect in data_runup['transects']:
#                    if str(transect['id']) == str(tid):
#                        d = datetime.utcnow().strftime("%Y%m%dZ%H")
#                        for time in transect['times']:
#                            if time['date'] == d:
#                                transect['times'] = [time]
#                                result.append(transect)
#                                break
#                            break
#                        return jsonify({'transects': result})
#        except IOError as e:
#            return jsonify({"details": "Service Unavailable", "result": "error"})
