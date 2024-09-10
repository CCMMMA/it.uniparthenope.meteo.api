from datetime import datetime
from flask_restx import Namespace, Resource
from flask import jsonify, request
from geojson import FeatureCollection

from core.GetParams import get_params
from core.Tiles import Tiles
from core.MemcachedMethodHandlers import get_resource, set_resource
import json
import app

api = Namespace('apps', description='Apps API')


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

# TESTED AND WORKING
@api.route('/owm/<string:prod>/<string:placeprefix>/<int:z>/<int:x>/<int:y>.geojson', methods=['GET', 'OPTIONS'])
class AppsOwmWeatherProdPlacePrefix(Resource):
    @api.doc()
    def get(self, prod, placeprefix, z, x, y):
        """
        :example: /apps/owm/wrf5/prov/10/552/384.geojson
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({'date': None})
            res = app.tiles.get_weather_ex(prod, placeprefix, params, z, x, y)
            set_resource(request, res, app.cache, app.use_pymemcache)
        else:
            res = json.loads(res)
        return jsonify(res)


# TESTED AND WORKING
@api.route('/sais/index')
class AppsSaisRisk(Resource):
    @api.doc()
    def get(self):
        """
        :example: /apps/sais/index
        :returns: json -- the return josn.
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
