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

api = Namespace('v2', description='V2 API')

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
    def get(self):
        return core.RRSResponseHandlers.get_latest_weather_report_jsonify()


# ORIGINAL : Internal server error
@api.route('/weatherreports/latest/<string:field>/json')
class WeatherReportsLatestJson(Resource):
    def get(self, field):
        # sanitizer = Sanitizer()  da studiare
        return core.RRSResponseHandlers.get_field_lwr_jsonify(field)


# TESTED AND WORKING
@api.route('/weatherreports/json')
class WeatherReportsJson(Resource):
    def get(self):
        return core.RRSResponseHandlers.get_all_weather_reports_jsonify()

# FROM ORIGINAL : Internal Server Error
# TESTED - 1 problem
@api.route('/slurm/storage')
class SlurmStorage(Resource):
    def get(self):
        ss = SlurmServices(app.application.config)
        res = ss.get_storage_status()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/slurm/info')
class SlurmInfo(Resource):
    def get(self):
        ss = SlurmServices(app.application.config)
        res = ss.sinfo()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/slurm/queue')
class SlurmInfo(Resource):
    def get(self):
        ss = SlurmServices(app.application.config)
        res = ss.squeue()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/carousel')
class Carousel(Resource):
    @api.doc(security='Basic Auth')
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
    @api.doc(security='Basic Auth')
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
    def get(self):
        return jsonify(baseMaps)


# TESTED AND WORKING
@api.route('/basemaps/<string:name>')
class BaseMapsByName(Resource):
    def get(self, name):
        return jsonify(baseMaps[name])


# TESTED AND WORKING
@api.route('/layers')
class Layers(Resource):
    def get(self):
        return jsonify(layers)


# TESTED AND WORKING
# example : name = info
@api.route('/layers/<string:name>')
class LayersByName(Resource):
    def get(self, name):
        return jsonify(layers[name])


# TESTED AND WORKING
@api.route('/maps')
class Maps(Resource):
    def get(self):
        return jsonify(maps)


# TESTED AND WORKING
# example : name = weather
@api.route('/maps/<string:name>')
class MapsByName(Resource):
    def get(self, name):
        return jsonify(maps[name])


# TESTED AND WORKING
@api.route('/navbar')
class NavBar(Resource):
    @api.doc(security='Basic Auth')
    @roles_from_token
    def get(self, **kwargs):
        """Returns the navbar
        :example: /navbar
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        roles = kwargs["roles"]
        cms = CMS(app.application.config)
        params = get_params({'lang': 'en-US'})
        res = cms.get_navbar(roles, params)
        return jsonify({"navbar": res})


# TESTED AND WORKING
@api.route('/pages')
class Pages(Resource):
    @api.doc(security='Basic Auth')
    @roles_from_token
    def get(self, **kwargs):
        """Returns the pages list
        :example: /pages
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        cms = CMS(app.application.config)
        res = cms.get_pages(params)
        return jsonify({"pages": res})


# TESTED AND WORKING
@api.route('/pages/<string:page>')
class PageByPageId(Resource):
    @api.doc(security='Basic Auth')
    @roles_from_token
    def get(self, page, **kwargs):
        """Returns the page content by a given id
        :example: /pages/about_us
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        params["userId"] = kwargs["userId"]
        cms = CMS(app.application.config)
        res = cms.get_page_by_id(roles, page, params)
        return jsonify(res)

    @api.doc(security='Basic Auth')
    @api.expect(page_model)
    @roles_from_token
    def post(self, page, **kwargs):
        """Returns the page content by a given id
        :example: /pages/about_us
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        roles = kwargs["roles"]
        params = get_params({'lang': 'en-US'})
        params["userId"] = kwargs["userId"]
        cms = CMS(app.application.config)
        res = cms.set_page_by_id(roles, page, api.payload, params)
        return jsonify(res)


@api.route('/auth/login')
class AuthLoginByToken(Resource):
    @api.doc(security='Basic Auth')
    @token_required
    def get(self, **kwargs):
        """Returns the roles of an authenticated users (if any)
        :example: /v2/auth/loginToken
        :param value: The token value.
        :type prod: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        token = kwargs["token"]
        ls = LoginServices(app.application.config)
        res = ls.auth2Token(token)
        return jsonify(res)
