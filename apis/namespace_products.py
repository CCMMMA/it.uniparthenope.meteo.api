import hashlib
import app
import base64
# import logging
from core.Logger import logger
import json
from flask_restx import Namespace, Resource
from flask import jsonify, Response, make_response
from core.GetParams import get_params
from core.MemcachedMethodHandlers import get_resource, set_resource
from core.MeteoServices import MeteoServices, csvfy
from core.Places import Places
from flask import request
from core.GribServices import GribServices

##### Logging #####
# logger = logging.getLogger('main_logger')
#################


api = Namespace('products', description='Products API')

# TESTED AND WORKING
@api.route('/<string:prod>/<string:place>/avail')
class ProductsAvailable(Resource):
    @api.doc()
    def get(self, prod, place):
        """Returns the avilable products
        :param prod:
        :param place:
        :return: json
        :exampler: /products/rdr1/ca001/avail
        """
        params = get_params({
            'place': place,
            'prod': prod,
            'offset_pre': 1,
            'offset_post': 0,
            'date': None
        })
        res = app.meteo_services.getProductAvail(params)
        return jsonify(avail=res)


# TESTED AND WORKING
@api.route('/<string:prod>/<string:place>/avail/calendar')
class ProductsAvailableCalendar(Resource):
    @api.doc()
    def get(self, prod, place):
        """Returns the avaliable products.
        :exampler: /products/rdr1/ca001/avail/calendar
        :returns:  json -- the return json.
        """
        params = get_params({
            'place': place,
            'prod': prod,
            'start': None,
            'end': None,
            'timeZone': None,
            "baseUrl": "https://app.meteo.uniparthenope.it/index.html?page=products"
        })
        res = app.meteo_services.getProductAvailCalendar(params)
        return jsonify(res)


# TESTED AND WORKING
@api.route('/maps')
class ProductsMap(Resource):
    @api.doc()
    def get(self):
        """Returns the avaliable maps.
        :exampler: /products/maps
        :returns:  json -- the return json.
        """
        res = app.meteo_services.getMaps()
        return jsonify(maps=res)


# TESTED AND WORKING
@api.route('/<string:prod>/maps/themes')
class ProductsThemesByProd(Resource):
    @api.doc()
    def get(self, prod):
        """Returns the avaliable themes.
        :example: /produts/wrf5/maps/themes
        :returns:  json -- the return json.
        """
        res = app.meteo_services.getThemes(prod)
        return jsonify(themes=res)


# TESTED AND WORKING
@api.route('')
class Products(Resource):
    @api.doc()
    def get(self):
        """Returns the avaliable products.
        :example: /products
        :returns:  json -- the return json.
        """
        res = app.meteo_services.getProds()
        return jsonify(products=res)


# TESTED AND WORKING
@api.route('/<string:prod>')
class ProductsOutputsByProd(Resource):
    @api.doc()
    def get(self, prod):
        """Returns all avaliable outputs given a product code
        :example: /products/wrf5/outputs
        :param prod: The code of the product.
        :type prod: str.
        :returns:  json -- the return josn.
        """

        if prod is None or prod == "" or prod == "null":
            prod="wrf5"

        res = app.meteo_services.getProds(prod)
        return jsonify(outputs=res)


# TESTED AND WORKING
@api.route('/<string:prod>/outputs')
class ProductsOutputsByProd(Resource):
    @api.doc()
    def get(self, prod):
        """Returns all avaliable outputs given a product code
        :example: /products/wrf5/outputs
        :param prod: The code of the product.
        :type prod: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = app.meteo_services.getOutputs(prod)
        return jsonify(outputs=res)


# TESTED AND WORKING
@api.route('/<string:prod>/fields')
class ProductsFieldsByProd(Resource):
    @api.doc()
    def get(self, prod):
        """Returns all avaliable fields given a product code
        :example: /products/wrf5/fields
        :param prod: The code of the product.
        :type prod: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = app.meteo_services.getFields(prod)
        return jsonify(fields=res)


# TESTED AND WORKING
@api.route('/<string:prod>/forecast/<string:place>')
class ProductsForecastByProdAndPlace(Resource):
    @api.doc()
    def get(self, prod, place):
        """Returns the forecast for a product given a place
        :example: /products/wrf5/forecast/com63049
        :param prod: The code of the product.
        :type prod: str.
        :param place: The code of the place.
        :type place: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'place': place,
                'filter': None,
                'prod': prod,
                'date': None,
                'opt': ""
            })
            res = app.meteo_services.modelOutput(params)
            if 'result' in res and "ok" not in res['result']:
                return jsonify(res)
            if place == 'VEB1500013' :
                res['scs'] = 0
            if place == 'VEB1500018' :
                res['winds'] = 0
            set_resource(request, res, app.cache, app.use_pymemcache)
        return jsonify(eval(str(res)))

# TESTED AND WORKING
@api.route('/<string:prod>/forecast/<string:place>/plot/image')
class ProductsForecastMapByProdAndPlace(Resource):
    @api.doc()
    def get(self, prod, place):
        """Returns the forecast plot as image or url given a product code and a place
        :example: /products/ww33/forecast/ca001/plot/image
        :param prod: The code of the product.
        :type prod: str.
        :param place: The code of the place.
        :type place: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """

        
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')        
  
        # print(f"\n\n origin : {origin} -- referer : {referer} \n\n")

        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'id': place,
                'filter': None,
                'place': place,
                'prod': prod,
                'output': 'gen',
                'date': None,
                'width': 1024,
                'height': 768,
                'dry': "false",
                'opt': ""
            })

            # Section to distinguish mytilex calls from those of the weather portal.
            # MytilEX case.
            if origin == 'https://meteo.uniparthenope.it' :
                params['watermark'] = True

            # Weather portal case.
            #elif origin == None :
            #    print(f"\n\n request from weather portal. \n\n")

            # print(f"\n\n params : {params} \n\n", flush=True)
            
            (mapData, imageName) = app.meteo_services.ModelPlotImage(app.use_disk_cached, params)
        
            res = {
                'plot': base64.b64encode(mapData).decode('utf-8'),
                # 'plot': mapData,
                'imageName': imageName
            }
            set_resource(request, res, app.cache, app.use_pymemcache)
        else:
            res = eval(res)
        
        response = make_response(base64.b64decode(res['plot']))
        # response = make_response(res['plot'])
        response.headers['Content-Type'] = 'image/png'
        # response.headers['Content-Disposition'] = 'attachment; filename=' + res['imageName']
        return response


# FROM ORIGINAL API : Load failed
@api.route('/<string:prod>/forecast/<string:domain>/grib/text')
class ProductsForecastGribJsonByProdAndDomain(Resource):
    @api.doc()
    def get(self, prod, domain):
        """Returns the forecast map as image or url given a product code and a place
        :param domain:
        :example: /products/wrf5/forecast/d02/grib/text
        :param prod: The code of the product.
        :type prod: str.
        :returns:  json -- the return json.
        ------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'domain': domain,
                'prod': prod,
                'date': None,
                'opt': ""
            })
            json_data = app.grib_services.asText(params)
            res = json_data
            set_resource(request, res, app.cache, app.use_pymemcache)
        return Response(res, mimetype='text/plain')


# PROBLEM WITH INSTALLATION OF WRF-PYTHON
@api.route('/<string:prod>/forecast/<string:domain>/grib/json')
class ProductsForecastGribJsonByProdAndDomain(Resource):
    @api.doc()
    def get(self, prod, domain):
        """Returns the forecast map as image or url given a product code and a place
        :example: /products/wrf5/forecast/d02/grib/json
        :param prod: The code of the product.
        :type prod: str.
        :param prod: The code of the place.
        :type prod: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'domain': domain,
                'prod': prod,
                'date': None,
                'opt': ""
            })
            json_data = app.grib_services.asJson(params)
            res = json_data
            set_resource(request, res, app.cache, app.use_pymemcache)
        return jsonify(res)


# TESTED AND WORKING
@api.route('/<string:prod>/forecast/<string:place>/plot')
class ProductsForecastMapByProdAndPlace(Resource):
    @api.doc()
    def get(self, prod, place):
        """Returns the forecast plot as image or url given a product code and a place
        :example: /products/ww33/forecast/ca001/plot
        :param prod: The code of the product.
        :type prod: str.
        :param place: The code of the place.
        :type place: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
        """

        if prod == 'rdr1':
            return None

        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'id': place,
                'filter': None,
                'place': place,
                'prod': prod,
                'output': 'gen',
                'date': None,
                'mode': 'grads',
                'run': None,
                'width': None,
                'height': None,
                'dry': 'true',
                'opt': ""
            })
            (mapData, imageName) = app.meteo_services.ModelPlotUrl(app.use_disk_cached, params)

            if 'code' in mapData:
                return jsonify({
                    "details": mapData,
                    "result": "error",
                    "map": {
                        "link": app.application.config['NOIMAGE_URL']
                    }
                })
            res = {
                'map': mapData,
                'imageName': imageName
            }

            if 'data' in params['opt']:
                forecastData = app.meteo_services.modelOutput(params)
                if 'result' in forecastData and 'ok' in forecastData['result']:
                    res['forecast'] = forecastData['forecast']
                    if 'place' in params['opt']:
                        res['place'] = forecastData['place']
                    if 'place' in params['opt']:
                        res['fields'] = forecastData['fields']

            set_resource(request, res, app.cache, app.use_pymemcache)
        else:
           res = eval(res)

        params = get_params({'dry': 'true'})
        if 'dry' in params and params['dry'] is not None and params['dry'].lower() == "false":
            response = app.application.make_response(res['map'])
            # print(str(res['map']))
            response.headers['Content-Type'] = 'image/png'
            # response.headers['Content-Disposition'] = 'attachment; filename='+res['imageName']
            return response
        return jsonify(res)


# TESTED AND WORKING
@api.route('/<string:prod>/forecast/legend/<string:position>/<string:output>')
class ProductsForecastBarByProdAndPositionAndOutput(Resource):
    @api.doc()
    def get(self, prod, position, output):
        """Returns the image bar as image given a product code, a position and an output parameter.
        :example: /products/ww33/forecast/bar/h/crd

        :param prod: The code of the product.
        :type prod: str.
        :param position: Position of the bar [ left | right | top | bottom ).
        :type place: str.
        :param output: Output parameter of the bar.
        :type output: str.
        :returns: image.
        -------------------------------------------------------------------------------------------

        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'width': None,
                'height': None,
                'date': None
            })
            bar_data = app.meteo_services.getlegenddata(prod, position, output, params)
            res = {
                'legend': base64.b64encode(bar_data).decode('utf-8')
            }
            set_resource(request, res, app.cache, app.use_pymemcache)
        else:
          res = eval(res)

        response = make_response(base64.b64decode(res['legend']))
        response.headers['Content-Type'] = 'image/png'

        return response


# ORIGINAL : Internal Server Error
@api.route('/<string:prod>/forecast/legend/<string:position>/<string:output>/ncwms')
class ProductsForecastBarByProdAndPositionAndOutputFromNcWMS(Resource):
    @api.doc()
    def get(self, prod, position, output):
        """Returns the image bar as image given a product code, a position and an output parameter.
        :example: /products/ww33/forecast/bar/h/crd/ncwms
        :param prod: The code of the product.
        :type prod: str.
        :param position: Position of the bar [ left | right | top | bottom ).
        :type place: str.
        :param output: Output parameter of the bar.
        :type output: str.
        :returns: image.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'width': None,
                'height': None,
                'date': None
            })
            bar_data = app.meteo_services.getlegenddata1(prod, position, output, params)
            res = {
                'legend': base64.b64encode(bar_data).decode('utf-8')
            }
            set_resource(request, res, app.cache, app.use_pymemcache)
        else:
          res = eval(res)

        response = make_response(base64.b64decode(res['legend']))
        response.headers['Content-Type'] = 'image/png'

        return response

# TESTED AND WORKING
@api.route('/<string:prod>/timeseries/<string:place>')
class ProductsTimeseriesByProdAndPlace(Resource):
    @api.doc()
    def get(self, prod, place):
        """Returns ......................
        :example: /products/ww33/timeseries/ca001
        :param prod: The code of the product.
        :type prod: str.
        :param place: The code of the place.
        :type place: str.
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'place': place,
                'prod': prod,
                'hours': 0,
                'step': 1,
                'md5': None,
                'date': None,
                'opt': ""
            })
            time_series_data = app.meteo_services.timeseries(params)
            if 'result' in time_series_data and "ok" not in time_series_data['result']:
                return jsonify(time_series_data)
            res = time_series_data
            set_resource(request, res, app.cache, app.use_pymemcache)
        else:
          # log.info("[*][*][*][*] Res : " + str(res))
          res = eval(res)
        return jsonify(res)


# TESTED AND WORKING
@api.route('/<string:prod>/timeseries/<string:place>/csv')
class ProductsTimeSeriesByProdAndPlaceByCsv(Resource):
    @api.doc()
    def get(self, prod, place):
        """Returns ......................
        :example: /products/wrf3/timeseries/ca001/csv
        :param prod: The code of the product.
        :type prod: str.
        :param place: The code of the place.
        :type place: str.
        :returns: csv -- the return csv.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({
                'place': place,
                'prod': prod,
                'step': 1,
                'md5': None,
                'date': None,
                'opt': ""
            })
            params['opt'] = params['opt'] + ",fields"
            time_series_data = app.meteo_services.timeseries(params)

            if 'result' in time_series_data and "ok" not in time_series_data['result']:
                return jsonify(time_series_data)

            res = time_series_data
            set_resource(request, res, app.cache, app.use_pymemcache)
        else:
          res = eval(res)

        return csvfy(res)


# ORIGINAL : Internal Server Error
@api.route('/<string:prod>/timeseries/<string:place>/chart')
class ProductsTimeSeriesByProdAndPlaceByChart(Resource):
    @api.doc()
    def get(self, prod, place):
        """Returns an image url given a product code and a place code.
        :example: /products/ww33/timeseries/ca001/chart
        :param prod: The code of the product.
        :type prod: str.
        :param place: The code of the place.
        :type place: str.
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({'id': place, 'filter': None, 'prod': prod})
            places = Places(app.application.config)
            placeData = places.get_place_by_id(place, params)
            # print("placeData: ", placeData)
            if placeData is None:
                return jsonify({
                    "details": "Place not found.",
                    "result": "error"
                })

            params = get_params({
                'place': place,
                'prod': prod,
                'output': 'gen',
                'hours': None,
                'step': None
            })
            chartData = app.meteo_services.modelcharturl(params)
            if 'code' in chartData:
                return jsonify({
                    "details": chartData,
                    "result": "error"
                })
            res = {
                'chart': chartData,
                'place': placeData
            }
            set_resource(request, res, app.cache, app.use_pymemcache)
        return jsonify(res)
        

# Nuova route aggiunta - quella che mancava 
@api.route('/<prod>/forecast/<place>/map/image')
class ProductsForecastMapByProdAndPlace(Resource):
    @api.doc()
    def get(self,prod,place ):
        """Returns the forecast map as image or url given a product code and a place

        :example: /products/ww33/forecast/ca001/map

        :param prod: The code of the product.
        :type prod: str.
        :param place: The code of the place.
        :type place: str.
        :returns:  json -- the return josn.
        -------------------------------------------------------------------------------------------
    
        """
        res=get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({'id':place,'filter':None, 'place':place, 'prod': prod, 'output':'gen', 'date':None,'width': 1024, 'height': 768,'dry':"false",'opt':""})
            ms = MeteoServices(app.application.config)
            (mapData,imageName) = ms.modelmapurl_or_image(app.use_disk_cached, params)
            res = {
                'map': base64.b64encode(mapData).decode('utf-8'),
                'imageName': imageName
            }
            set_resource(request,res, app.cache, app.use_pymemcache)
        else:
            res = eval(res)
                        
        response = make_response(base64.b64decode(res['map']))
        response.headers['Content-Type'] = 'image/png'
        return response