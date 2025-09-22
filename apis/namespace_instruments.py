import json
from flask_restx import Namespace, Resource
from flask import jsonify, Response, make_response, request
from core.MeteoServices import MeteoServices
import app
from core.MemcachedMethodHandlers import get_resource, set_resource


api = Namespace('instruments', description='Instruments API')


# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('')
class Instruments(Resource):
    @api.doc()
    def get(self):
        """Returns the avaliable instruments.
        :example: /products
        :returns:  json -- the return json.
        """

        res = get_resource(request, app.cache, app.use_pymemcache)
        res = None          # To Test 

        # Check Memcache
        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            res = None         # To Test 

            # Check Diskcache
            if res is None:

                ms = MeteoServices(app.application.config)
                res = ms.getInstruments()

                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])

                #return jsonify(res)
               
        return res


        