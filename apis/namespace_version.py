"""RESTX namespace exposing API version metadata."""

from flask_restx import Namespace, Resource
from flask import current_app, jsonify

from .versioning import IMPLEMENTATION_VERSION

api = Namespace('version', description='Service version and runtime environment metadata.')


# TESTED AND WORKING -- NO CACHE USE
@api.route('')
class Version(Resource):
    """Resource handler for version operations."""
    @api.doc(
        summary="Get service version information",
        responses={200: "Version payload returned successfully"}
    )
    def get(self):
        """
        Return the deployed API version together with the configured runtime environment label.

        Example:
        `GET /version`
        """
        res = {
            'version': IMPLEMENTATION_VERSION,
            'environment': current_app.config['ENV'],
        }
        return jsonify(res)
