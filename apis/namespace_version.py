from flask_restx import Namespace, Resource
from flask import jsonify
import app

api = Namespace('version', description='Service version and runtime environment metadata.')


# TESTED AND WORKING -- NO CACHE USE
@api.route('')
class Version(Resource):
    @api.doc(
        summary="Get service version information",
        responses={200: "Version payload returned successfully"}
    )
    def get(self):
        """
        Return the deployed API version together with the configured runtime environment label.
        """
        res = {'version': '4.01', 'environment': app.application.config['ENV']}
        return jsonify(res)
