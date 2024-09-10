from flask_restx import Namespace, Resource
from flask import send_file
import os
import app

api = Namespace('webcam', description='Webcam API')


# TESTED AND WORKING
# I DON'T HAVE WEBCAM DIRECTORY
@api.route("/<string:place>/<string:location>/<string:cam>")
class Webcam(Resource):
    @api.doc()
    def get(self, place, location, cam):
        """
        Returns the latest image from the specified webcam.
        :example: /webcam/com63049/castelsantelmo/nord
        :returns:  json -- the return json.
        -------------------------------------------------------------------------------------------
        """
        f_name = "/home/ccmmma/prometeo/data/webcam/" + place + "/" + location + "/" + cam + ".jpg"
        if not os.path.isfile(f_name):
            f_name = app.application.config['NOIMAGE_PATH']
        return send_file(f_name, mimetype='image/jpg')
