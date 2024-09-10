from flask_restx import Namespace, Resource
from flask import jsonify
from core.MeteoServices import MeteoServices
from core.GetParams import get_params
import app

api = Namespace('legal', description='Legal API')


# TESTED AND WORKING
@api.route('/disclaimer')
class LegalDiscaimer(Resource):
    @api.doc()
    def get(self):
        """Returns the Disclaimer.
        :example: /legal/disclaimer
        :returns:  json -- the return json.
        -------------------------------------------------------------------------------------------
        """
        ms = MeteoServices(app.application.config)
        params = get_params({'lang': 'en-US'})
        res = ms.getLegalDisclaimer(params)
        return jsonify(res)


# TESTED AND WORKING
@api.route('/privacy')
class LegalPrivacy(Resource):
    @api.doc()
    def get(self):
        """Returns the Privacy.
        :example: /legal/privacy
        :returns:  json -- the return json.
        -------------------------------------------------------------------------------------------
        """
        ms = MeteoServices(app.application.config)
        params = get_params({'lang': 'en-US'})
        res = ms.getLegalPrivacy(params)
        return jsonify(res)
