"""RESTX namespace for version 2 endpoints, CMS content, and protected resources."""

import base64
import hashlib
from functools import wraps
import pymongo
import requests
import simplejson
from flask_restx import Namespace, Resource, fields
from flask import jsonify, request
import app
from core.LoginServices import LoginServices
from core.SlurmServices import SlurmServices
import core.RRSResponseHandlers
import core.SlurmServices
from core.CMS import CMS
from core.GetParams import get_params
from core.DataStructuresV2 import maps, baseMaps, layers

api = Namespace('v2', description='Version 2 endpoints for weather reports, CMS content, Slurm data, and authenticated resources.')

page_model = api.model("page", {
    "_id": fields.String("Page unique id"),
    "author": fields.String("The author of the page (userId)")
})


def _extract_bearer_token():
    """Return the bearer token from the Authorization header when available."""
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        return None

    parts = auth_header.split(None, 1)
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


def _json_status_response(payload, default_status=200):
    """Return a JSON response using the status encoded in a legacy payload when present."""
    status_code = payload.get("statusCode", default_status) if isinstance(payload, dict) else default_status
    try:
        status_code = int(status_code)
    except (TypeError, ValueError):
        status_code = default_status
    return jsonify(payload), status_code


def _resolve_mapping_detail(data, name, field_name):
    """Resolve one entry from a static mapping and return a 404 payload when missing."""
    if name not in data:
        return jsonify({"errMsg": f"{field_name} not found.", "statusCode": 404}), 404
    return jsonify(data[name])


def token_required(f):
    """Protect an endpoint by requiring a valid authorization token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        """Implement decorated function."""
        kwargs['token'] = _extract_bearer_token()
        return f(*args, **kwargs)

    return decorated_function


def roles_from_token(f):
    """Extract role information from an authorization token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        """Implement decorated function."""
        token = _extract_bearer_token()
        roles = []
        userId = None
        if token:
            ls = LoginServices(app.application.config)
            res = ls.auth2Token(token)
            if "meteo" in res:
                userId = res['user']['userId']
                roles = list(res["meteo"]["roles"])
                roles.append("auth")
        # Check if user have been authenticated
        if not "auth" in roles:
            roles.append("all")
        kwargs['roles'] = roles
        kwargs['userId'] = userId
        return f(*args, **kwargs)

    return decorated_function


# TESTED AND WORKING
@api.route('/weatherreports/latest/json')
class WeatherReportsLatestJson(Resource):
    """Resource handler for weather reports latest json operations."""
    @api.doc(summary="Get the latest weather report payload", responses={200: "Latest weather report returned"})
    def get(self):
        """
        Return the latest weather report as JSON.

        Example:
        `GET /v2/weatherreports/latest/json`
        """
        return core.RRSResponseHandlers.get_latest_weather_report_jsonify()


# ORIGINAL : Internal server error
@api.route('/weatherreports/latest/<string:field>/json')
class WeatherReportsLatestJson(Resource):
    """Resource handler for weather reports latest json operations."""
    @api.doc(summary="Get a field from the latest weather report", params={"field": "Weather report field name"}, responses={200: "Weather report field returned", 404: "Field not found"})
    def get(self, field):
        """
        Return a single field from the latest weather report.

        Example:
        `GET /v2/weatherreports/latest/title/json`
        """
        # sanitizer = Sanitizer()  da studiare
        return core.RRSResponseHandlers.get_field_lwr_jsonify(field)


# TESTED AND WORKING
@api.route('/weatherreports/json')
class WeatherReportsJson(Resource):
    """Resource handler for weather reports json operations."""
    @api.doc(summary="Get all weather reports", responses={200: "Weather reports returned"})
    def get(self):
        """
        Return all weather reports exposed by the service.

        Example:
        `GET /v2/weatherreports/json`
        """
        return core.RRSResponseHandlers.get_all_weather_reports_jsonify()

# FROM ORIGINAL : Internal Server Error
# TESTED - 1 problem
@api.route('/slurm/storage')
class SlurmStorage(Resource):
    """Resource handler for slurm storage operations."""
    @api.doc(summary="Get Slurm storage status", responses={200: "Storage status returned"})
    def get(self):
        """
        Return storage information collected from the Slurm environment.

        Example:
        `GET /v2/slurm/storage`
        """
        ss = SlurmServices(app.application.config)
        res = ss.get_storage_status()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/slurm/info')
class SlurmInfo(Resource):
    """Resource handler for slurm info operations."""
    @api.doc(summary="Get Slurm cluster information", responses={200: "Slurm information returned"})
    def get(self):
        """
        Return general cluster information from Slurm.

        Example:
        `GET /v2/slurm/info`
        """
        ss = SlurmServices(app.application.config)
        res = ss.sinfo()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/slurm/queue')
class SlurmInfo(Resource):
    """Resource handler for slurm info operations."""
    @api.doc(summary="Get Slurm queue information", responses={200: "Slurm queue returned"})
    def get(self):
        """
        Return the current Slurm queue snapshot.

        Example:
        `GET /v2/slurm/queue`
        """
        ss = SlurmServices(app.application.config)
        res = ss.squeue()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/carousel')
class Carousel(Resource):
    """Resource handler for carousel operations."""
    @api.doc(summary="Get carousel content", security='Bearer', responses={200: "Carousel content returned"})
    @roles_from_token
    def get(self, **kwargs):
        """Handle GET requests for this resource."""
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        cms = CMS(app.application.config)
        res = cms.get_carousel(roles, params)
        return jsonify({"carousel": res})


# TESTED AND WORKING
@api.route('/cards')
class Cards(Resource):
    """Resource handler for cards operations."""
    @api.doc(summary="Get card content", security='Bearer', responses={200: "Cards content returned"})
    @roles_from_token
    def get(self, **kwargs):
        """Handle GET requests for this resource."""
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        cms = CMS(app.application.config)
        res = cms.get_cards(roles, params)
        return jsonify({"cards": res})


# TESTED AND WORKING
@api.route('/basemaps')
class BaseMaps(Resource):
    """Resource handler for base maps operations."""
    @api.doc(summary="List basemaps", responses={200: "Basemap catalog returned"})
    def get(self):
        """Handle GET requests for this resource."""
        return jsonify(baseMaps)


# TESTED AND WORKING
@api.route('/basemaps/<string:name>')
class BaseMapsByName(Resource):
    """Resource handler for base maps by name operations."""
    @api.doc(summary="Get a basemap by name", params={"name": "Basemap identifier"}, responses={200: "Basemap returned", 404: "Basemap not found"})
    def get(self, name):
        """Handle GET requests for this resource."""
        return _resolve_mapping_detail(baseMaps, name, "Basemap")


@api.route('/basemap/detail')
class BaseMapDetail(Resource):
    """Legacy compatibility alias for basemap detail lookups."""
    @api.doc(summary="Get a basemap by legacy detail route", params={"name": "Basemap identifier"}, responses={200: "Basemap returned", 404: "Basemap not found"})
    def get(self):
        """Handle GET requests for the legacy basemap detail alias."""
        name = request.args.get("name") or request.args.get("id")
        if not name:
            return jsonify({"errMsg": "Basemap not found.", "statusCode": 404}), 404
        return _resolve_mapping_detail(baseMaps, name, "Basemap")


# TESTED AND WORKING
@api.route('/layers')
class Layers(Resource):
    """Resource handler for layers operations."""
    @api.doc(summary="List layers", responses={200: "Layer catalog returned"})
    def get(self):
        """Handle GET requests for this resource."""
        return jsonify(layers)


# TESTED AND WORKING
# example : name = info
@api.route('/layers/<string:name>')
class LayersByName(Resource):
    """Resource handler for layers by name operations."""
    @api.doc(summary="Get a layer by name", params={"name": "Layer identifier"}, responses={200: "Layer returned", 404: "Layer not found"})
    def get(self, name):
        """Handle GET requests for this resource."""
        return _resolve_mapping_detail(layers, name, "Layer")


# TESTED AND WORKING
@api.route('/maps')
class Maps(Resource):
    """Resource handler for maps operations."""
    @api.doc(summary="List maps", responses={200: "Map catalog returned"})
    def get(self):
        """Handle GET requests for this resource."""
        return jsonify(maps)


# TESTED AND WORKING
# example : name = weather
@api.route('/maps/<string:name>')
class MapsByName(Resource):
    """Resource handler for maps by name operations."""
    @api.doc(summary="Get a map definition by name", params={"name": "Map identifier"}, responses={200: "Map definition returned", 404: "Map not found"})
    def get(self, name):
        """Handle GET requests for this resource."""
        return _resolve_mapping_detail(maps, name, "Map")


# TESTED AND WORKING
@api.route('/navbar')
class NavBar(Resource):
    """Resource handler for nav bar operations."""
    @api.doc(summary="Get navbar content", security='Bearer', responses={200: "Navbar content returned"})
    @roles_from_token
    def get(self, **kwargs):
        """
        Return the CMS-derived navigation bar payload filtered by the caller roles.

        Example:
        `GET /v2/navbar`
        """
        roles = kwargs["roles"]
        cms = CMS(app.application.config)
        params = get_params({'lang': 'en-US'})
        res = cms.get_navbar(roles, params)
        return jsonify({"navbar": res})


# TESTED AND WORKING
@api.route('/pages')
class Pages(Resource):
    """Resource handler for pages operations."""
    @api.doc(summary="List pages", security='Bearer', responses={200: "Pages list returned"})
    @roles_from_token
    def get(self, **kwargs):
        """
        Return the list of CMS-managed pages available to the caller.

        Example:
        `GET /v2/pages`
        """
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        cms = CMS(app.application.config)
        res = cms.get_pages(roles, params)
        return jsonify({"pages": res})


# TESTED AND WORKING
@api.route('/pages/<string:page>')
class PageByPageId(Resource):
    """Resource handler for page by page id operations."""
    @api.doc(summary="Get a page by identifier", security='Bearer', params={"page": "Page identifier"}, responses={200: "Page returned", 404: "Page not found"})
    @roles_from_token
    def get(self, page, **kwargs):
        """
        Return a CMS page payload by page identifier.

        Example:
        `GET /v2/pages/about_us`
        """
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        params["userId"] = kwargs["userId"]
        cms = CMS(app.application.config)
        res = cms.get_page_by_id(roles, page, params)
        return jsonify(res)

    @api.doc(summary="Create or update a page by identifier", security='Bearer', params={"page": "Page identifier"}, responses={200: "Page persisted successfully", 400: "Invalid page payload", 403: "User not allowed"})
    @api.expect(page_model)
    @roles_from_token
    def post(self, page, **kwargs):
        """
        Persist a CMS page payload for the specified page identifier.

        Example:
        `POST /v2/pages/about_us`
        """
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        params["userId"] = kwargs["userId"]
        cms = CMS(app.application.config)
        res = cms.set_page_by_id(roles, page, api.payload, params)
        return jsonify(res)


@api.route('/page/detail')
class PageDetail(Resource):
    """Legacy compatibility alias for page detail lookups."""
    @api.doc(summary="Get a page by legacy detail route", security='Bearer', params={"page": "Page identifier"}, responses={200: "Page returned", 404: "Page not found"})
    @roles_from_token
    def get(self, **kwargs):
        """Handle GET requests for the legacy page-detail alias."""
        page = request.args.get("page") or request.args.get("id")
        if not page:
            return jsonify({"errMsg": "Page not found.", "statusCode": 404}), 404

        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        params["userId"] = kwargs["userId"]
        cms = CMS(app.application.config)
        res = cms.get_page_by_id(roles, page, params)
        return jsonify(res)


@api.route('/auth/login')
class AuthLoginByToken(Resource):
    """Resource handler for auth login by token operations."""
    @api.doc(summary="Resolve authentication information from a bearer token", security='Bearer', responses={200: "Authentication information returned", 401: "Missing or invalid token"})
    @token_required
    def get(self, **kwargs):
        """
        Validate the bearer token received in the `Authorization` header and return the associated authentication payload.

        Example:
        `GET /v2/auth/login`
        """
        token = kwargs["token"]
        ls = LoginServices(app.application.config)
        res = ls.auth2Token(token)
        return _json_status_response(res)
