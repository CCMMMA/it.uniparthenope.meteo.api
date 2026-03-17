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


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split()[1]
        kwargs['token'] = token
        return f(*args, **kwargs)

    return decorated_function


def roles_from_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        roles = []
        userId = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split()[1]
            ls = LoginServices(app.application.config)
            res = ls.auth2Token(token)
            if "meteo" in res:
                userId = res['user']['userId']
                roles = res["meteo"]["roles"]
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
    @api.doc(summary="Get the latest weather report payload", responses={200: "Latest weather report returned"})
    def get(self):
        return core.RRSResponseHandlers.get_latest_weather_report_jsonify()


# ORIGINAL : Internal server error
@api.route('/weatherreports/latest/<string:field>/json')
class WeatherReportsLatestJson(Resource):
    @api.doc(summary="Get a field from the latest weather report", params={"field": "Weather report field name"}, responses={200: "Weather report field returned", 404: "Field not found"})
    def get(self, field):
        # sanitizer = Sanitizer()  da studiare
        return core.RRSResponseHandlers.get_field_lwr_jsonify(field)


# TESTED AND WORKING
@api.route('/weatherreports/json')
class WeatherReportsJson(Resource):
    @api.doc(summary="Get all weather reports", responses={200: "Weather reports returned"})
    def get(self):
        return core.RRSResponseHandlers.get_all_weather_reports_jsonify()

# FROM ORIGINAL : Internal Server Error
# TESTED - 1 problem
@api.route('/slurm/storage')
class SlurmStorage(Resource):
    @api.doc(summary="Get Slurm storage status", responses={200: "Storage status returned"})
    def get(self):
        ss = SlurmServices(app.application.config)
        res = ss.get_storage_status()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/slurm/info')
class SlurmInfo(Resource):
    @api.doc(summary="Get Slurm cluster information", responses={200: "Slurm information returned"})
    def get(self):
        ss = SlurmServices(app.application.config)
        res = ss.sinfo()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/slurm/queue')
class SlurmInfo(Resource):
    @api.doc(summary="Get Slurm queue information", responses={200: "Slurm queue returned"})
    def get(self):
        ss = SlurmServices(app.application.config)
        res = ss.squeue()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/carousel')
class Carousel(Resource):
    @api.doc(summary="Get carousel content", security='Bearer', responses={200: "Carousel content returned"})
    @roles_from_token
    def get(self, **kwargs):
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        cms = CMS(app.application.config)
        res = cms.get_carousel(roles, params)
        return jsonify({"carousel": res})


# TESTED AND WORKING
@api.route('/cards')
class Cards(Resource):
    @api.doc(summary="Get card content", security='Bearer', responses={200: "Cards content returned"})
    @roles_from_token
    def get(self, **kwargs):
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        cms = CMS(app.application.config)
        res = cms.get_cards(roles, params)
        return jsonify({"cards": res})


# TESTED AND WORKING
@api.route('/basemaps')
class BaseMaps(Resource):
    @api.doc(summary="List basemaps", responses={200: "Basemap catalog returned"})
    def get(self):
        return jsonify(baseMaps)


# TESTED AND WORKING
@api.route('/basemaps/<string:name>')
class BaseMapsByName(Resource):
    @api.doc(summary="Get a basemap by name", params={"name": "Basemap identifier"}, responses={200: "Basemap returned", 404: "Basemap not found"})
    def get(self, name):
        return jsonify(baseMaps[name])


# TESTED AND WORKING
@api.route('/layers')
class Layers(Resource):
    @api.doc(summary="List layers", responses={200: "Layer catalog returned"})
    def get(self):
        return jsonify(layers)


# TESTED AND WORKING
# example : name = info
@api.route('/layers/<string:name>')
class LayersByName(Resource):
    @api.doc(summary="Get a layer by name", params={"name": "Layer identifier"}, responses={200: "Layer returned", 404: "Layer not found"})
    def get(self, name):
        return jsonify(layers[name])


# TESTED AND WORKING
@api.route('/maps')
class Maps(Resource):
    @api.doc(summary="List maps", responses={200: "Map catalog returned"})
    def get(self):
        return jsonify(maps)


# TESTED AND WORKING
# example : name = weather
@api.route('/maps/<string:name>')
class MapsByName(Resource):
    @api.doc(summary="Get a map definition by name", params={"name": "Map identifier"}, responses={200: "Map definition returned", 404: "Map not found"})
    def get(self, name):
        return jsonify(maps[name])


# TESTED AND WORKING
@api.route('/navbar')
class NavBar(Resource):
    @api.doc(summary="Get navbar content", security='Bearer', responses={200: "Navbar content returned"})
    @roles_from_token
    def get(self, **kwargs):
        """
        Return the CMS-derived navigation bar payload filtered by the caller roles.
        """
        roles = kwargs["roles"]
        cms = CMS(app.application.config)
        params = get_params({'lang': 'en-US'})
        res = cms.get_navbar(roles, params)
        return jsonify({"navbar": res})


# TESTED AND WORKING
@api.route('/pages')
class Pages(Resource):
    @api.doc(summary="List pages", security='Bearer', responses={200: "Pages list returned"})
    @roles_from_token
    def get(self, **kwargs):
        """
        Return the list of CMS-managed pages available to the caller.
        """
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        cms = CMS(app.application.config)
        res = cms.get_pages(params)
        return jsonify({"pages": res})


# TESTED AND WORKING
@api.route('/pages/<string:page>')
class PageByPageId(Resource):
    @api.doc(summary="Get a page by identifier", security='Bearer', params={"page": "Page identifier"}, responses={200: "Page returned", 404: "Page not found"})
    @roles_from_token
    def get(self, page, **kwargs):
        """
        Return a CMS page payload by page identifier.
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
        """
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        params["userId"] = kwargs["userId"]
        cms = CMS(app.application.config)
        res = cms.set_page_by_id(roles, page, api.payload, params)
        return jsonify(res)


@api.route('/auth/login')
class AuthLoginByToken(Resource):
    @api.doc(summary="Resolve authentication information from a bearer token", security='Bearer', responses={200: "Authentication information returned", 401: "Missing or invalid token"})
    @token_required
    def get(self, **kwargs):
        """
        Validate the bearer token received in the `Authorization` header and return the associated authentication payload.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        token = kwargs["token"]
        ls = LoginServices(app.application.config)
        res = ls.auth2Token(token)
        return jsonify(res)
