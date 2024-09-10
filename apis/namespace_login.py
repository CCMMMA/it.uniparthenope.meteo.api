from flask_restx import Namespace, fields, Resource
from flask import jsonify
from core.LoginServices import LoginServices
import app

api = Namespace('users', description='Login API')

user_model = api.model("user", {
    "name": fields.String("The user name."),
    "pass": fields.String("The user password")
})

# TESTED AND WORKING
@api.route('/login')
class UserLogin(Resource):
    @api.doc()
    @api.expect(user_model)
    def post(self):
        """Returns the roles of an authenticated users (if any)
        :example: /user/login
        :param user: The user name.
        :type prod: str.
        :param pass: The user password.
        :type place: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        params = api.payload
        ms = LoginServices(app.application.config)
        res = ms.authentication_login(params['name'], params['pass'])
        return jsonify(res)

