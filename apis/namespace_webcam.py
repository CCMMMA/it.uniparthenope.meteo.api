from flask_restx import Namespace, Resource
from flask import send_file
import os
import app

api = Namespace('webcam', description='Latest webcam image retrieval endpoints.')


# TESTED AND WORKING -- NO CACHE USE
# I DON'T HAVE WEBCAM DIRECTORY
@api.route("/<string:place>/<string:location>/<string:cam>")
class Webcam(Resource):
    @api.doc(
        summary="Get the latest webcam image",
        params={
            "place": "Place code used in the webcam filesystem hierarchy",
            "location": "Location subdirectory for the webcam",
            "cam": "Camera identifier without extension"
        },
        responses={200: "Image returned successfully", 404: "Image resource not found"}
    )
    def get(self, place, location, cam):
        """
        Return the latest available JPEG image for the specified webcam path, falling back to the configured no-image asset when necessary.
        """
        f_name = "/home/ccmmma/prometeo/data/webcam/" + place + "/" + location + "/" + cam + ".jpg"
        if not os.path.isfile(f_name):
            f_name = app.application.config['NOIMAGE_PATH']
        return send_file(f_name, mimetype='image/jpg')
