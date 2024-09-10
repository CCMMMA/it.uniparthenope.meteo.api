from flask_restx import Namespace, Resource
from flask import jsonify
import app

api = Namespace('version', description='Version API')


# TESTED AND WORKING
@api.route('')
class Version(Resource):
    @api.doc()
    def get(self):
        """
        Returns API version
        :example: /version
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = {'version': '4.01', 'environment': app.application.config['ENV']}
        return jsonify(res)
