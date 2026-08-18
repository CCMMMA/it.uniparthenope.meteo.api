"""Administrative reporting resources for the governed API."""

from flask import current_app, jsonify, request
from flask_restx import Namespace, Resource

from apis.authentication import require_api_key
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION


api = Namespace("api-v1-admin", description="Protected API administration resources.")


@api.route("/usage")
class ApiV1UsageReport(Resource):
    """Expose bounded consumer-attributed usage aggregates."""

    @api.doc(summary="Report API usage", security="apiKey", params={"limit": "Recent event sample size (1-1000)"})
    @require_api_key("keys:admin")
    def get(self):
        """Return aggregate and recent events without credential secrets."""
        limit = request.args.get("limit", 100, type=int)
        service = current_app.extensions[RUNTIME_SERVICES_EXTENSION].api_keys
        return jsonify(service.usage_report(limit=limit))
