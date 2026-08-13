"""RESTX namespace exposing instrument inventory endpoints."""

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

api = Namespace('instruments', description='Instrument inventory and instrument-detail endpoints.')

@api.route('')
class Instruments(Resource):
    """Resource handler for instruments operations."""
    @api.doc(
        summary="List instruments",
        responses={200: "Instrument catalog returned successfully", 502: "Upstream instrument service unavailable"}
    )
    def get(self):
        """
        Return the available instruments payload retrieved from the upstream Signal K integration.

        Example:
        `GET /instruments`
        """

        ms = MeteoServices(app.application.config)
        res = ms.getInstruments()

        '''
        print("\n\n")
        logger.info(f"res : {res}")
        print("\n\n")
        '''

        for elem in res.items():
            logger.debug("instrument entry: %s", elem)

        return jsonify(res)


@api.route('/<string:identification>')
class InstrumentsContext(Resource):
    """Resource handler for instruments context operations."""
    @api.doc(
        summary="Get a specific instrument",
        params={"identification": "Instrument identifier to resolve from the upstream instruments payload"},
        responses={200: "Instrument payload returned successfully", 404: "Instrument not found"}
    )
    def get(self, identification):
        """
        Return a single instrument record selected by identifier from the upstream instruments payload.

        Example:
        `GET /instruments/station-01`
        """

        ms = MeteoServices(app.application.config)
        res = ms.getInstruments()

        for ws_id, ws_data in res.items():
            if ws_id == identification:
                return jsonify(ws_data)
        
        return jsonify("Identification not found!"), 404

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

        
