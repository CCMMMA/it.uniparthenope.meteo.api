"""RESTX namespace for place discovery and geospatial lookup."""

from flask import current_app, jsonify, request
from flask_restx import Namespace, Resource

from core.GetParams import get_params
from core.MemcachedMethodHandlers import get_resource, load_cached_json, set_resource
from core.Places import Places
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION


api = Namespace('places', description='Place discovery, lookup, and geospatial search endpoints.')


def _runtime_services():
    """Return the dependencies shared by cache-aware place handlers."""
    return current_app.extensions[RUNTIME_SERVICES_EXTENSION]


@api.route('')
class GetAllPlaces(Resource):
    """Resource handler for get all places operations."""

    @api.doc(summary="List all places", responses={200: "Places collection returned successfully"})
    def get(self):
        """Return the complete place collection available to the API."""
        services = _runtime_services()
        res = get_resource(request, services.memory_cache, services.memory_cache_enabled)

        if res is None:
            res = services.disk_cache.get(
                request, services.disk_cache_ttl, services.disk_cache_enabled
            )
            if res is None:
                places = Places(current_app.config)
                res = places.get_all_places("places")
                for obj in res:
                    obj.pop("_id")

                services.disk_cache.set(request, res, 'json')
                set_resource(
                    request, res, services.memory_cache, services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                )

        return jsonify(load_cached_json(res, res))


@api.route('/search/byname/<string:name>')
class PlacesSearchByName(Resource):
    """Resource handler for places search by name operations."""

    @api.doc(
        summary="Search places by name",
        params={"name": "Free-text place name to search"},
        responses={200: "Matching places returned successfully"},
    )
    def get(self, name):
        """Search places whose names match the requested text."""
        services = _runtime_services()
        res = get_resource(request, services.memory_cache, services.memory_cache_enabled)

        if res is None:
            res = services.disk_cache.get(
                request, services.disk_cache_ttl, services.disk_cache_enabled
            )
            if res is None:
                name = name.replace("+", " ")
                params = get_params({'name': name, 'filter': None, 'prod': None, 'limit': None})
                places = Places(current_app.config)
                res = places.get_places_by_name(name, params)
                services.disk_cache.set(request, res, 'json')
                set_resource(
                    request, res, services.memory_cache, services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                )
        else:
            res = load_cached_json(res, [])
        return jsonify(res)


@api.route('/search/byname/autocomplete')
class PlacesSearchByNameAutocomplete(Resource):
    """Resource handler for places search by name autocomplete operations."""

    @api.doc(
        summary="Autocomplete places by term",
        params={"term": "Autocomplete term supplied as a query parameter"},
        responses={200: "Autocomplete results returned successfully"},
    )
    def get(self):
        """Return compact place suggestions for frontend search use."""
        services = _runtime_services()
        res = get_resource(request, services.memory_cache, services.memory_cache_enabled)

        if res is None:
            res = services.disk_cache.get(
                request, services.disk_cache_ttl, services.disk_cache_enabled
            )
            if res is None:
                places = Places(current_app.config)
                params = get_params({'term': None})
                options = {
                    'filter': ['com', 'porti', 'prov', 'reg', 'ca', 'iim', 'med', 'UNI', 'VET', 'VEB', 'la'],
                    'limit': 20,
                }
                matches = places.get_places_by_name(params['term'], options)
                res = [
                    {'label': place['long_name']['it'], 'id': place['id']}
                    for place in matches
                ]
                services.disk_cache.set(request, res, 'json')
                set_resource(
                    request, res, services.memory_cache, services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                )
        else:
            res = load_cached_json(res)
        return jsonify(res)


@api.route('/<string:identifier>')
class PlacesByIdentifier(Resource):
    """Resource handler for places by identifier operations."""

    @api.doc(
        summary="Get a place by identifier",
        params={"identifier": "Canonical place identifier"},
        responses={200: "Place returned successfully", 404: "Place not found"},
    )
    def get(self, identifier):
        """Return a single place by its canonical identifier."""
        services = _runtime_services()
        res = get_resource(request, services.memory_cache, services.memory_cache_enabled)

        if res is None:
            res = services.disk_cache.get(
                request, services.disk_cache_ttl, services.disk_cache_enabled
            )
            if res is None:
                params = get_params({'id': identifier, 'filter': None, 'prod': None})
                places = Places(current_app.config)
                res = places.get_place_by_id(identifier, params)
                if res is None:
                    return jsonify({"details": "Place not found.", "result": "error"})

                services.disk_cache.set(request, res, 'json')
                set_resource(
                    request, res, services.memory_cache, services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                )
        else:
            res = load_cached_json(res)
        return jsonify(res)


@api.route('/search/bycoords/<float:latitude>/<float:longitude>')
class PlacesSearchByCoords(Resource):
    """Resource handler for places search by coordinates operations."""

    @api.doc(
        summary="Search places near coordinates",
        params={
            "latitude": "Latitude in decimal degrees",
            "longitude": "Longitude in decimal degrees",
        },
        responses={200: "Nearby places returned successfully"},
    )
    def get(self, latitude, longitude):
        """Search places near the given geographic coordinates."""
        services = _runtime_services()
        res = get_resource(request, services.memory_cache, services.memory_cache_enabled)

        if res is None:
            res = services.disk_cache.get(
                request, services.disk_cache_ttl, services.disk_cache_enabled
            )
            if res is None:
                params = get_params({'range': None, 'filter': None, 'prod': None, 'limit': None})
                places = Places(current_app.config)
                res = places.get_places_by_ll(float(longitude), float(latitude), params)
                services.disk_cache.set(request, res, 'json')
                set_resource(
                    request, res, services.memory_cache, services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                )
        else:
            res = load_cached_json(res, [])
        return jsonify(res)


@api.route('/search/byboundingbox/<float:minLatitude>/<float:minLongitude>/<float:maxLatitude>/<float:maxLongitude>')
class PlacesSearchByBoundingBox(Resource):
    """Resource handler for place bounding-box searches."""

    @api.doc(
        summary="Search places inside a bounding box",
        params={
            "minLatitude": "Southern boundary latitude",
            "minLongitude": "Western boundary longitude",
            "maxLatitude": "Northern boundary latitude",
            "maxLongitude": "Eastern boundary longitude",
        },
        responses={200: "Places inside the bounding box returned successfully"},
    )
    def get(self, minLatitude, minLongitude, maxLatitude, maxLongitude):
        """Search places contained inside the given bounding box."""
        services = _runtime_services()
        res = get_resource(request, services.memory_cache, services.memory_cache_enabled)

        if res is None:
            res = services.disk_cache.get(
                request, services.disk_cache_ttl, services.disk_cache_enabled
            )
            if res is None:
                params = get_params({'filter': None, 'diag': None, 'zoom': None})
                places = Places(current_app.config)
                res = places.get_places_by_bb(
                    float(minLongitude), float(minLatitude),
                    float(maxLongitude), float(maxLatitude), params,
                )
                services.disk_cache.set(request, res, 'json')
                set_resource(
                    request, res, services.memory_cache, services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                )
        else:
            res = load_cached_json(res, [])
        return jsonify(res)
