from flask_restx import Namespace, fields, Resource
from flask import jsonify
from core.LoginServices import LoginServices
import app

api = Namespace('users', description='Authentication endpoints for legacy user login flows.')

user_model = api.model("user", {
    "name": fields.String("The user name."),
    "pass": fields.String("The user password")
})

# TESTED AND WORKING -- NO CACHE USE
@api.route('/login')
class UserLogin(Resource):
    @api.doc(
        summary="Authenticate a user",
        responses={200: "Authentication payload returned", 400: "Invalid payload", 401: "Authentication failed"}
    )
    @api.expect(user_model)
    def post(self):
        """
        Authenticate a user and return the downstream role and profile payload produced by the login service.

        Example body:
        `{"name": "student", "pass": "secret"}`
        """
        params = api.payload
        ms = LoginServices(app.application.config)
        res = ms.authentication_login(params['name'], params['pass'])
        return jsonify(res)
