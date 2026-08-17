"""RESTX namespace exposing legal and privacy content."""

from flask_restx import Namespace, Resource
from flask import current_app, jsonify

from core.GetParams import get_params
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION

api = Namespace('legal', description='Legal and compliance content endpoints.')


# TESTED AND WORKING -- NO CACHE USE 
@api.route('/disclaimer')
class LegalDiscaimer(Resource):
    """Resource handler for legal discaimer operations."""
    @api.doc(
        summary="Get disclaimer content",
        responses={200: "Disclaimer payload returned successfully"}
    )
    def get(self):
        """
        Return the legal disclaimer content configured for the platform.

        Example:
        `GET /legal/disclaimer`
        """
        meteo_services = current_app.extensions[RUNTIME_SERVICES_EXTENSION].meteo
        params = get_params({'lang': 'en-US'})
        res = meteo_services.getLegalDisclaimer(params)
        return jsonify(res)


# TESTED AND WORKING -- NO CACHE USE 
@api.route('/privacy')
class LegalPrivacy(Resource):
    """Resource handler for legal privacy operations."""
    @api.doc(
        summary="Get privacy content",
        responses={200: "Privacy payload returned successfully"}
    )
    def get(self):
        """
        Return the privacy information configured for the platform.

        Example:
        `GET /legal/privacy`
        """
        meteo_services = current_app.extensions[RUNTIME_SERVICES_EXTENSION].meteo
        params = get_params({'lang': 'en-US'})
        res = meteo_services.getLegalPrivacy(params)
        return jsonify(res)
