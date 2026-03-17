#################################################
#   
#   Università Degli Studi di Napoli Parthenope 
#
#
# Authors: 
#    Prof. Raffaele Montella
#    Dario Caramiello   
#
#################################################

from flask_restx import Namespace, Resource
from flask import jsonify, Response, make_response, request

from core.Logger import logger
from core.MeteoServices import MeteoServices
from core.MemcachedMethodHandlers import get_resource, set_resource

import json
import app

api = Namespace('instruments', description='Instruments API')

@api.route('')
class Instruments(Resource):
    @api.doc()
    def get(self):
        """Returns the avaliable instruments.
        :example: /products
        :returns:  json -- the return json.
        """

        ms = MeteoServices(app.application.config)
        res = ms.getInstruments()

        '''
        print("\n\n")
        logger.info(f"res : {res}")
        print("\n\n")
        '''

        for elem in res.items():
            print("\n\n")
            logger.info(f"elem : {elem}")
            print("\n\n")

        return jsonify(res)


@api.route('/<string:identification>')
class InstrumentsContext(Resource):
    @api.doc()
    def get(self, identification):

        ms = MeteoServices(app.application.config)
        res = ms.getInstruments()

        for ws_id, ws_data in res.items():
            if ws_id == identification:
                return ws_data
        
        return "Identification not found!"

'''
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
'''

        