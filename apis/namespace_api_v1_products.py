"""Version 1 product discovery and metadata resources."""

from flask import current_app, jsonify
from flask_restx import Namespace, Resource

from core.GetParams import get_params
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION


api = Namespace(
    "api-v1-products",
    description="Stable version 1 product discovery, metadata, and availability resources.",
)


def _meteo():
    """Return the application-owned meteorological service."""
    return current_app.extensions[RUNTIME_SERVICES_EXTENSION].meteo


@api.route("")
class ApiV1Products(Resource):
    """Expose the version 1 product catalogue."""

    @api.doc(summary="List products", responses={200: "Product catalogue returned"})
    def get(self):
        """Return the same stable catalogue envelope as the legacy resource."""
        return jsonify(products=_meteo().getProds())


@api.route("/maps")
class ApiV1ProductMaps(Resource):
    """Expose product map metadata."""

    @api.doc(summary="List product maps", responses={200: "Map metadata returned"})
    def get(self):
        """Return map definitions used by product visualizations."""
        return jsonify(maps=_meteo().getMaps())


@api.route("/<string:prod>/maps/themes")
class ApiV1ProductThemes(Resource):
    """Expose themes for one product."""

    @api.doc(summary="List product themes", params={"prod": "Product code"})
    def get(self, prod):
        """Return visualization themes for the selected product."""
        return jsonify(themes=_meteo().getThemes(prod))


@api.route("/<string:prod>")
class ApiV1Product(Resource):
    """Expose metadata for one product."""

    @api.doc(summary="Get product metadata", params={"prod": "Product code"})
    def get(self, prod):
        """Return the selected product's established metadata envelope."""
        return jsonify(outputs=_meteo().getProds(prod))


@api.route("/<string:prod>/outputs")
class ApiV1ProductOutputs(Resource):
    """Expose output definitions for one product."""

    @api.doc(summary="List product outputs", params={"prod": "Product code"})
    def get(self, prod):
        """Return output definitions for the selected product."""
        return jsonify(outputs=_meteo().getOutputs(prod))


@api.route("/<string:prod>/fields")
class ApiV1ProductFields(Resource):
    """Expose field definitions for one product."""

    @api.doc(summary="List product fields", params={"prod": "Product code"})
    def get(self, prod):
        """Return field definitions for the selected product."""
        return jsonify(fields=_meteo().getFields(prod))


@api.route("/<string:prod>/<string:place>/availability")
class ApiV1ProductAvailability(Resource):
    """Expose product availability for one place."""

    @api.doc(
        summary="Get product availability",
        params={"prod": "Product code", "place": "Place identifier"},
    )
    def get(self, prod, place):
        """Return the established availability envelope under canonical v1 naming."""
        params = get_params(
            {
                "place": place,
                "prod": prod,
                "offset_pre": 1,
                "offset_post": 0,
                "date": None,
            }
        )
        return jsonify(avail=_meteo().getProductAvail(params))


@api.route("/<string:prod>/<string:place>/availability/calendar")
class ApiV1ProductAvailabilityCalendar(Resource):
    """Expose calendar-oriented product availability."""

    @api.doc(
        summary="Get product availability calendar",
        params={"prod": "Product code", "place": "Place identifier"},
    )
    def get(self, prod, place):
        """Return calendar availability while preserving the legacy payload schema."""
        params = get_params(
            {
                "place": place,
                "prod": prod,
                "start": None,
                "end": None,
                "timeZone": None,
                "baseUrl": "https://app.meteo.uniparthenope.it/index.html?page=products",
            }
        )
        return jsonify(_meteo().getProductAvailCalendar(params))
