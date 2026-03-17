from flask_restx import Namespace, Resource
from core.Box import Box
from flask import jsonify
from core.GetParams import get_params

api = Namespace('box', description='Box-oriented content endpoints.')


# TESTED AND WORKING -- NO CACHE USE
@api.route('/today/<string:place>')
class BoxToday(Resource):
    @api.doc(
        summary="Get today's box payload for a place",
        params={"place": "Place identifier used by the box service"},
        responses={200: "Box content returned successfully", 404: "Box content not found"}
    )
    def get(self, place):
        """
        Return the current box content for the requested place identifier.
        """
        params = get_params({place: 'com63049'})
        box = Box()
        result = box.get_today(params)
        return jsonify(result)
