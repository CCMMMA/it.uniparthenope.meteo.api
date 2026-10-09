"""Application-facing endpoints for tiled payload services."""

import json

from flask import current_app, jsonify, request
from flask_restx import Namespace, Resource

from core.GetParams import get_params
from core.MemcachedMethodHandlers import get_resource, set_resource
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION
from core.Tiles import InvalidTileError


api = Namespace('apps', description='Application-facing integration endpoints and tiled payload services.')


@api.route('/owm/<string:prod>/<string:placeprefix>/<int:z>/<int:x>/<int:y>.geojson', methods=['GET', 'OPTIONS'])
class AppsOwmWeatherProdPlacePrefix(Resource):
    """Resource handler for application-facing OWM weather tiles."""

    @api.doc(
        summary="Get application weather tile data",
        params={
            "prod": "Forecast product code",
            "placeprefix": "Place prefix filter used to constrain the response",
            "z": "Tile zoom level",
            "x": "Tile x coordinate",
            "y": "Tile y coordinate",
        },
        responses={200: "GeoJSON-style payload returned successfully", 400: "Unsupported request"},
    )
    def get(self, prod, placeprefix, z, x, y):
        """Return the requested application-oriented weather tile payload."""
        if placeprefix == "reg":
            return {'message': 'The place \'reg\' is not used'}

        services = current_app.extensions[RUNTIME_SERVICES_EXTENSION]
        res = get_resource(
            request, services.memory_cache, services.memory_cache_enabled
        )

        if res is None:
            res = services.disk_cache.get(
                request, services.disk_cache_ttl, services.disk_cache_enabled
            )
            if res is None:
                params = get_params({'date': None})
                try:
                    res, cacheable = services.tiles.get_weather_tile(
                        prod, placeprefix, params, z, x, y
                    )
                except InvalidTileError as error:
                    return {'message': str(error)}, 400
                # A tile whose places still wait for their forecast file is
                # served but not cached, so it fills in as soon as data lands.
                if not cacheable:
                    return jsonify(res)
                services.disk_cache.set(
                    request, res, 'json', services.disk_cache_enabled
                )

            # Promote disk hits as well as freshly generated tiles. This avoids
            # repeated disk I/O and JSON decoding after a memory-cache eviction.
            set_resource(
                request,
                res,
                services.memory_cache,
                services.memory_cache_enabled,
                current_app.config['TTL_MEMCACHED'],
            )
        else:
            res = json.loads(res)
        return jsonify(res)
