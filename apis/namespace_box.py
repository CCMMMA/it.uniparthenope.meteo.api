from flask_restx import Namespace, Resource
from core.Box import Box
from flask import jsonify
from core.GetParams import get_params

api = Namespace('box', description='Box API')


# TESTED AND WORKING
@api.route('/today/<string:place>')
class BoxToday(Resource):
    @api.doc()
    def get(self, place):
        """
        :example: /places/today/ca001
        :param place: The code of the place.
        :type prod: str.
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        params = get_params({place: 'com63049'})
        box = Box()
        result = box.get_today(params)
        return jsonify(result)
