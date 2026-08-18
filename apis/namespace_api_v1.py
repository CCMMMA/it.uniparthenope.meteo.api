"""Discovery endpoint for the first governed API contract."""

from flask import current_app, jsonify
from flask_restx import Namespace, Resource

from .versioning import CURRENT_API_BASE_PATH, CURRENT_API_VERSION, IMPLEMENTATION_VERSION


api = Namespace(
    "api-v1",
    description="Metadata and discovery links for the version 1 API contract.",
)


@api.route("")
class ApiV1Discovery(Resource):
    """Describe the current contract without altering legacy endpoints."""

    @api.doc(
        summary="Discover the version 1 API contract",
        responses={200: "API contract metadata returned successfully"},
    )
    def get(self):
        """Return stable metadata and links for API clients."""
        return jsonify(
            {
                "name": "University of Naples Parthenope Meteo API",
                "apiVersion": CURRENT_API_VERSION,
                "basePath": CURRENT_API_BASE_PATH,
                "status": "current",
                "implementationVersion": IMPLEMENTATION_VERSION,
                "environment": current_app.config["ENV"],
                "legacy": {
                    "supported": True,
                    "unversionedBasePath": "/",
                    "existingV2BasePath": "/v2",
                },
                "links": {
                    "documentation": "/",
                    "openapi": "/swagger.json",
                    "products": f"{CURRENT_API_BASE_PATH}/products",
                    "usageReport": f"{CURRENT_API_BASE_PATH}/admin/usage",
                },
            }
        )
