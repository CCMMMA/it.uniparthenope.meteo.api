from flask_restx import Namespace, Resource
from flask import jsonify
from core.MeteoServices import MeteoServices
from core.GetParams import get_params
import app

api = Namespace('legal', description='Legal and compliance content endpoints.')


# TESTED AND WORKING -- NO CACHE USE 
@api.route('/disclaimer')
class LegalDiscaimer(Resource):
    @api.doc(
        summary="Get disclaimer content",
        responses={200: "Disclaimer payload returned successfully"}
    )
    def get(self):
        """
        Return the legal disclaimer content configured for the platform.
        """
        ms = MeteoServices(app.application.config)
        params = get_params({'lang': 'en-US'})
        res = ms.getLegalDisclaimer(params)
        return jsonify(res)


# TESTED AND WORKING -- NO CACHE USE 
@api.route('/privacy')
class LegalPrivacy(Resource):
    @api.doc(
        summary="Get privacy content",
        responses={200: "Privacy payload returned successfully"}
    )
    def get(self):
        """
        Return the privacy information configured for the platform.
        """
        ms = MeteoServices(app.application.config)
        params = get_params({'lang': 'en-US'})
        res = ms.getLegalPrivacy(params)
        return jsonify(res)
