"""Authentication helpers for legacy login flows."""

import base64
import hashlib

import requests
import simplejson
from core.MongoDbHandlers import MongoDBHandlers


class LoginServices:
    """Service or helper that encapsulates login services behavior."""
    config = {}
    path = ""
    __statusCode = {'200': {'code': '200', 'msg': 'OK'}, '205': {'code': '205', 'msg': 'No Content'},
                    '231': {'code': '231', 'msg': 'Info Not Available'}, '400': {'code': '400', 'msg': 'Bad Request'},
                    '401': {'code': '401', 'msg': 'Unauthorized'}, '404': {'code': '404', 'msg': 'Not Found'}}

    def __init__(self, config):
        """Initialize login services state."""
        self.cfg = config

    def authentication_login(self, user, password):
        """Implement authentication login for login services."""
        retval = {}
        headers = {"Content-type": "application/json"}
        payload = {"name": user, "pass": password}
        r = requests.post('https://meteo.uniparthenope.it/user/login?_format=json', headers=headers, data=simplejson.dumps(payload))
        json_r = simplejson.loads(r.text)
        try:
            if json_r['message'] != "":
                pass
        except:
            r = requests.get('https://meteo.uniparthenope.it/jdrupal/connect?_format=json', headers=headers, cookies=r.cookies)
        retval = simplejson.loads(r.text)
        return retval


    def fill_invalid_token(self):
        """Implement fill invalid token for login services."""
        # Auth service not found
        retval = {
            "errMsg": "Token not valid.",
            "statusCode": 401
        }
        return retval

    def fill_user_not_recognized(self):
        """Implement fill user not recognized for login services."""
        # User not recognised
        retval = {
            "errMsg": "Invalid Username or Password!",
            "statusCode": 401
        }
        return retval

    def fill_auth_service_not_found(self):
        """Implement fill auth service not found for login services."""
        # Auth service not found
        retval = {
            "errMsg": "Auth service not found!",
            "statusCode": 404
        }
        return retval

    def fill_local_user(self,result):
        """Implement fill local user for login services."""
        # The user is a local user
        retval = {
            "user": {"userId": result["_id"]},
            "meteo": {"roles": result["roles"]}
        }
        return retval

    def fill_infrastructure_user(self, userId):
        """Implement fill infrastructure user for login services."""

        # print "fill_infrastructure_user"
        # print "userId", str(userId)

        # The login is successful
        retval = {
            "user": {"userId": userId},
            "meteo": {"roles": []}
        }

        # Check if there is a local user profile
        # conn = pymongo.MongoClient()
        # db = conn[self.cfg['DATABASE']]
        # users = db['users']
        # query = {"_id": userId}
        # proj = {"roles": 1}

        # Perform the query
        # result = users.find_one(query, proj)

        result = MongoDBHandlers(self.config).get_query('users', {"_id": userId}, {"roles": 1})

        # Check if the user has a local profile
        if result is not None:
            # Add roles
            retval["meteo"]["roles"] = result["roles"]

        else:
            # The user is not present

            # Set the default role for auth users
            roles = []

            # Prepare data
            userData = {
                "_id": userId,
                "roles": roles
            }

            # Add the user
            # result = users.insert_one(userData)
            result = MongoDBHandlers(self.config).call_insert_one('users', userData)

            if result is not None:
                retval["meteo"]["errMsg"] = "Success: Local profile added"
            else:
                retval["meteo"]["errMsg"] = "Fail: Troubles in adding local profile"

        return retval

    def auth2Token(self, token):
        """Implement auth2 token for login services."""
        url = 'https://api.uniparthenope.it/auth/v1/login'
        retval = self.fill_invalid_token()
        if token is None or token == "":
            # print(str(retval))
            return retval
        headers = {
            "Content-type": "application/json",
            "Authorization": "Basic " + str(token)
        }
        # Decode the userId from the token
        base64_bytes = token.encode('utf-8')
        message_bytes = base64.b64decode(base64_bytes)
        message_decoded = message_bytes.decode('utf-8')
        if ":" not in message_decoded:
            return retval
        token_string_parts = message_decoded.split(":")
        if len(token_string_parts) != 2:
            return retval
        userId = token_string_parts[0]
        retval = self.fill_auth_service_not_found()
        jsonR = {}
        try:
            r = requests.get(url, headers=headers)  # , data=simplejson.dumps(payload))
            jsonR = simplejson.loads(r.text)
        except Exception as e:
            retval["exception"] = str(e)
            retval["responseText"] = r.text
            retval["url"] = url
            return retval
        # print "https://api.uniparthenope.it/auth/v1/login:",str(jsonR)
        # Check if the login failed
        if "errMsg" in jsonR:
            # The login failed
            # Open the connection to the database
            # conn = pymongo.MongoClient()
            # db = conn[self.cfg['DATABASE']]
            # users = db['users']
            # The user is not present
            password = token_string_parts[1]
            # Check if there is a local user
            query = {"_id": userId, "password": hashlib.md5(password.encode()).hexdigest()}
            proj = {"roles": 1}
            # Perform the query
            # result = users.find_one(query, proj)
            result = MongoDBHandlers(self.config).get_query_find_one('users', query, proj)
            # Check if the user is a local user
            if result is not None:
                # The user is a local user
                retval = self.fill_local_user(result)
            else:
                # User not recognised
                retval = self.fill_user_not_recognized()
        else:
            # The login is successful
            retval = self.fill_infrastructure_user(userId)
        return retval
