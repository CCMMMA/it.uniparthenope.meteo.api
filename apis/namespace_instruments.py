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
from flask import current_app, jsonify

from core.Logger import logger
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION

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

        meteo_services = current_app.extensions[RUNTIME_SERVICES_EXTENSION].meteo
        res = meteo_services.getInstruments()

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

        meteo_services = current_app.extensions[RUNTIME_SERVICES_EXTENSION].meteo
        res = meteo_services.getInstruments()

        for ws_id, ws_data in res.items():
            if ws_id == identification:
                return jsonify(ws_data)
        
        # Let Flask-RESTX serialize the string so the legacy JSON-string body is
        # preserved without nesting a Flask Response inside a response tuple.
        return "Identification not found!", 404
