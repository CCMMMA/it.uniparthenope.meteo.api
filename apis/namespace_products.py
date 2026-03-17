#################################################
#   
#   Università Degli Studi di Napoli Parthenope 
#
#
# Author: 
#    Prof. Raffaele Montella
#    Dario Caramiello   
#
#################################################

import hashlib
import app
import base64
import json
from types import SimpleNamespace
from flask_restx import Namespace, Resource
from flask import jsonify, Response, make_response, request, send_from_directory
from datetime import datetime

from core.Logger import logger
from core.GetParams import get_params
from core.MemcachedMethodHandlers import get_resource, set_resource, load_cached_json
from core.MeteoServices import MeteoServices, csvfy
from core.Places import Places
from core.GribServices import GribServices
from core.MakeArchivePaths import MakeArchivePaths

api = Namespace('products', description='Forecast products, plots, time series, GRIB exports, legends, and static product assets.')


def _cache_request_with_default_date():
    cache_url = request.url
    if "date" not in request.args:
        ncep_date = datetime.utcnow().strftime("%Y%m%dZ%H00")
        separator = '&' if '?' in cache_url else '?'
        cache_url = f"{cache_url}{separator}date={ncep_date}"
    return SimpleNamespace(url=cache_url)

# TESTED AND WORKING - NO CACHE USE 
@api.route('')
class Products(Resource):
    @api.doc(summary="List products", responses={200: "Product catalog returned successfully"})
    def get(self):
        """
        Return the catalog of available forecast products.

        Example:
        `GET /products`
        """
        res = app.meteo_services.getProds()
        return jsonify(products=res)

# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/<string:place>/avail')
class ProductsAvailable(Resource):
    @api.doc(summary="Get product availability for a place", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Availability payload returned successfully"})
    def get(self, prod, place):
        """
        Return the availability summary for a product and a place.

        Example:
        `GET /products/rdr1/ca001/avail`
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


# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/<string:place>/avail/calendar')
class ProductsAvailableCalendar(Resource):
    @api.doc(summary="Get product availability as a calendar payload", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Availability calendar returned successfully"})
    def get(self, prod, place):
        """
        Return product availability rendered as a calendar-oriented payload.

        Example:
        `GET /products/rdr1/ca001/avail/calendar`
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


# TESTED AND WORKING - NO CACHE USE 
@api.route('/maps')
class ProductsMap(Resource):
    @api.doc(summary="Get maps metadata", responses={200: "Maps metadata returned successfully"})
    def get(self):
        """
        Return the map metadata used by product visualizations.

        Example:
        `GET /products/maps`
        """
        res = app.meteo_services.getMaps()
        return jsonify(maps=res)


# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/maps/themes')
class ProductsThemesByProd(Resource):
    @api.doc(summary="Get themes for a product", params={"prod": "Product code"}, responses={200: "Theme metadata returned successfully"})
    def get(self, prod):
        """
        Return the map themes available for the selected product.

        Example:
        `GET /products/wrf5/maps/themes`
        """
        res = app.meteo_services.getThemes(prod)
        return jsonify(themes=res)


# TESTED AND WORKING - NO CACHE USE
@api.route('/<string:prod>')
class ProductsOutputsByProd(Resource):
    @api.doc(summary="Get product metadata", params={"prod": "Product code"}, responses={200: "Product metadata returned successfully"})
    def get(self, prod):
        """
        Return the metadata block for a single product.

        Example:
        `GET /products/wrf5`
        """

        if prod is None or prod == "" or prod == "null":
            prod="wrf5"

        res = app.meteo_services.getProds(prod)
        return jsonify(outputs=res)


# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/outputs')
class ProductsOutputsByProd(Resource):
    @api.doc(summary="List outputs for a product", params={"prod": "Product code"}, responses={200: "Outputs returned successfully"})
    def get(self, prod):
        """
        Return the list of outputs available for the selected product.

        Example:
        `GET /products/wrf5/outputs`
        """
        res = app.meteo_services.getOutputs(prod)
        return jsonify(outputs=res)


# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/fields')
class ProductsFieldsByProd(Resource):
    @api.doc(summary="List fields for a product", params={"prod": "Product code"}, responses={200: "Field metadata returned successfully"})
    def get(self, prod):
        """
        Return the fields that can be queried for the selected product.

        Example:
        `GET /products/wrf5/fields`
        """
        res = app.meteo_services.getFields(prod)
        return jsonify(fields=res)

# TESTED AND WORKING - USE MEMCACHE AND DISKCACHE 
@api.route('/<string:prod>/forecast/<string:place>')
class ProductsForecastByProdAndPlace(Resource):
    @api.doc(summary="Get forecast data for a product and place", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Forecast returned successfully", 404: "Forecast not available"})
    def get(self, prod, place):
        """
        Return the structured forecast payload for the selected product and place.

        Example:
        `GET /products/wrf5/forecast/com63049`
        """
        res = get_resource(request, app.cache, app.use_pymemcache)

        # Check Memcache
        if res is None:
            

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            # Check Diskcache 
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

                
                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
            

        return jsonify(load_cached_json(res, res))


'''
# TESTED AND WORKING - USE MEMCACHE -- OLD VERSION
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

            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        return jsonify(eval(str(res)))
'''

# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE
@api.route('/<string:prod>/forecast/<string:place>/plot/image')
class ProductsForecastMapByProdAndPlace(Resource):
    @api.doc(summary="Get rendered forecast plot image", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "PNG image returned successfully"})
    def get(self, prod, place):
        """
        Return a rendered PNG plot for the selected product and place.

        Example:
        `GET /products/ww33/forecast/ca001/plot/image`
        """

        cache_request = _cache_request_with_default_date()
        
        # Check Memecache
        res = get_resource(cache_request, app.cache, app.use_pymemcache)

        if res is None:

            res2 = app.diskcache.get(cache_request, app.diskcache_ttl, app.use_disk_cached)

            # Check Diskcache 
            if res2 is None:

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
                
                (mapData, imageName) = app.meteo_services.ModelPlotImage(app.use_disk_cached, params)
            
                res = {
                    'plot': base64.b64encode(mapData).decode('utf-8'),
                    # 'plot': mapData,
                    'imageName': imageName
                }
                
                # Save on Diskcache
                app.diskcache.set(cache_request, base64.b64encode(mapData).decode('utf-8'), 'plot')

                # Save on Memcache 
                set_resource(cache_request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
            
            else:
                # Data in Diskcache

                res = {
                    'plot': res2,
                    # 'imageName': imageName
                }

        else:
            # Data in Memcache

            res = load_cached_json(res, {})
        
        response = make_response(base64.b64decode(res['plot']))
        # response = make_response(res['plot'])
        response.headers['Content-Type'] = 'image/png'
        # response.headers['Content-Disposition'] = 'attachment; filename=' + res['imageName']
        return response

'''
# TESTED AND WORKING -- USE MEMCACHE -- OLD VERSION 
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
            
            (mapData, imageName) = app.meteo_services.ModelPlotImage(app.use_disk_cached, params)
        
            res = {
                'plot': base64.b64encode(mapData).decode('utf-8'),
                # 'plot': mapData,
                'imageName': imageName
            }
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        
        response = make_response(base64.b64decode(res['plot']))
        # response = make_response(res['plot'])
        response.headers['Content-Type'] = 'image/png'
        # response.headers['Content-Disposition'] = 'attachment; filename=' + res['imageName']
        return response
'''

# @api.route('/wrf5/forecast/<string:place>/<float:lat>/<float:lon>/plot/SkewT/image')
@api.route('/wrf5/forecast/plot/SkewT/image')
class ProductSkewTByProdAndPlace(Resource):
    @api.doc(summary="Get a Skew-T plot image", params={"date": "Optional forecast reference time as query parameter"}, responses={200: "Skew-T image returned successfully"})
    def get(self):
        """
        Return a Skew-T diagnostic plot as a PNG image.

        Examples:
        `GET /products/wrf5/forecast/plot/SkewT/image`
        `GET /products/wrf5/forecast/plot/SkewT/image?date=20250915Z1000`
        """
     
        cache_request = _cache_request_with_default_date()
        
        res = get_resource(cache_request, app.cache, app.use_pymemcache)

        if res is None:
            
            params = get_params({
                'prod': "wrf5",
                'lat': 40.856,
                'lon': 14.352,
                'date': None,
            })

            (mapData, imageName) = app.meteo_services.ModelPlotSkewT(app.use_disk_cached, params)

            res = {
                'plot': base64.b64encode(mapData).decode('utf-8'),
                # 'plot': mapData,
                'imageName': imageName
            }

            set_resource(cache_request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
  
        else:
            # Data in Memcache
            res = load_cached_json(res, {})
        
        response = make_response(base64.b64decode(res['plot']))
        # response = make_response(res['plot'])
        response.headers['Content-Type'] = 'image/png'
        # response.headers['Content-Disposition'] = 'attachment; filename=' + res['imageName']
        return response

@api.route('/<string:prod>/forecast/<string:place>/plot/alt')
class ProductsForecastPlotAndAlt(Resource):
    @api.doc(summary="Get plot alternative text payload", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Alternative text payload returned successfully"})
    def get(self, prod, place, language="en-US"):
        """
        Return an alternative-text style description payload for a generated plot.

        Example:
        `GET /products/wrf5/forecast/com63049/plot/alt`
        """
        params = get_params({
            'id': place,
            'filter': None,
            #'place': place,
            #'prod': prod,
            'output': 'gen',
            'date': None,
            'width': 1024,
            'height': 768,
            'dry': "false",
            'lang': language,
            'opt': ""
        })

        all_info_place = Places(app.application.config).get_place_by_id(place)
        long_name = all_info_place['long_name']['it']
        res = app.meteo_services.MakeJsonAlt(prod, long_name, params)

        return res


# TESTED AND WORKING -- USE MEMCACHE 
@api.route('/<string:prod>/forecast/<string:domain>/grib/text')
class ProductsForecastGribJsonByProdAndDomain(Resource):
    @api.doc(summary="Get GRIB-oriented text export", params={"prod": "Product code", "domain": "Forecast domain code"}, responses={200: "Text export returned successfully"})
    def get(self, prod, domain):
        """
        Return a text export derived from GRIB-oriented product data.

        Example:
        `GET /products/wrf5/forecast/d02/grib/text`
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
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        
        logger.debug("/grib/text response ready: %s bytes", len(res) if res is not None else 0)
        return Response(res, mimetype='text/plain')


# ERROR -- USE MEMCACHE 
@api.route('/<string:prod>/forecast/<string:domain>/grib/json')
class ProductsForecastGribJsonByProdAndDomain(Resource):
    @api.doc(summary="Get GRIB-oriented JSON export", params={"prod": "Product code", "domain": "Forecast domain code"}, responses={200: "JSON export returned successfully"})
    def get(self, prod, domain):
        """
        Return a JSON export derived from GRIB-oriented product data.

        Example:
        `GET /products/wrf5/forecast/d02/grib/json`
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
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        return jsonify(res)


# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('/<string:prod>/forecast/<string:place>/plot')
class ProductsForecastMapByProdAndPlace(Resource):
    @api.doc(summary="Get forecast plot metadata or inline image", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Plot payload returned successfully"})
    def get(self, prod, place):
        """
        Return plot metadata, and optionally inline image data, for the selected product and place.

        Example:
        `GET /products/ww33/forecast/ca001/plot`
        """
        
        res = get_resource(request, app.cache, app.use_pymemcache)

        # Check Memcache
        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            # Check Disckcache
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

                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        
        else:
           res = load_cached_json(res, {})

        params = get_params({'dry': 'true'})
        if 'dry' in params and params['dry'] is not None and params['dry'].lower() == "false":
            response = app.application.make_response(res['map'])
            # print(str(res['map']))
            response.headers['Content-Type'] = 'image/png'
            # response.headers['Content-Disposition'] = 'attachment; filename='+res['imageName']
            return response
        return jsonify(res)


'''
# TESTED AND WORKING -- USE MEMCACHE -- OLD VERSION 
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
        # TODO: hard-code -- to remove 
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

            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
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
'''

# TESTED AND WORKING -- USE MEMCACHE 
@api.route('/<string:prod>/forecast/legend/<string:position>/<string:output>')
class ProductsForecastBarByProdAndPositionAndOutput(Resource):
    @api.doc(summary="Get a legend image", params={"prod": "Product code", "position": "Legend position", "output": "Output code"}, responses={200: "Legend image returned successfully"})
    def get(self, prod, position, output):
        """
        Return a legend image for the selected product output.

        Example:
        `GET /products/ww33/forecast/legend/right/waveheight`
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
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
          res = load_cached_json(res, {})

        response = make_response(base64.b64decode(res['legend']))
        response.headers['Content-Type'] = 'image/png'

        return response


# ORIGINAL : Internal Server Error -- USE MEMCACHE 
@api.route('/<string:prod>/forecast/legend/<string:position>/<string:output>/ncwms')
class ProductsForecastBarByProdAndPositionAndOutputFromNcWMS(Resource):
    @api.doc(summary="Get a legend image through ncWMS-related generation", params={"prod": "Product code", "position": "Legend position", "output": "Output code"}, responses={200: "Legend image returned successfully"})
    def get(self, prod, position, output):
        """
        Return a legend image generated through the ncWMS-oriented path.

        Example:
        `GET /products/ww33/forecast/legend/right/waveheight/ncwms`
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
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
          res = load_cached_json(res, {})

        response = make_response(base64.b64decode(res['legend']))
        response.headers['Content-Type'] = 'image/png'

        return response


@api.route('/<string:prod>/plot/<string:output>/metacharts')
class ProductsPlotMetacharts(Resource):
    @api.doc(summary="Get plot metadata charts", params={"prod": "Product code", "output": "Output code"}, responses={200: "Metacharts payload returned successfully"})
    def get(self, prod, output):
        """
        Return plotting metadata used by downstream frontend chart rendering.

        Example:
        `GET /products/wrf5/plot/gen/metacharts`
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
       
        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, None, app.use_disk_cached)
      
            if res is None:
                
                meta_charts = app.meteo_services.plotmetacharts(prod, output)

                res = meta_charts

                app.diskcache.set(request, res, 'json')

                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
                
        else:
            res = load_cached_json(res, {})
        
        return jsonify(res)


# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('/<string:prod>/timeseries/<string:place>')
class ProductsTimeseriesByProdAndPlace(Resource):
    @api.doc(summary="Get timeseries data", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Timeseries returned successfully"})
    def get(self, prod, place):
        """
        Return the structured time-series payload for the selected product and place.

        Example:
        `GET /products/ww33/timeseries/ca001`
        """

        # Check Memcache
        res = get_resource(request, app.cache, app.use_pymemcache)

        if res is None:

            params = get_params({
                'place': place,
                'prod': prod,
                'date': None
            })

            path_archive_file = MakeArchivePaths.makePath(params['prod'], params['place'])            
            # Check Diskcache
            res = app.diskcache.get(request, app.diskcache_ttl, path_archive_file, app.use_disk_cached)
            
            if res is None:


                params = get_params({
                    'place': place,
                    'prod': prod,
                    'output': None,
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

                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])

        else:
            res = load_cached_json(res, {})
        
        return jsonify(res)


'''
# TESTED AND WORKING -- USE MEMCACHE -- OLD VERSION
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
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
          # log.info("[*][*][*][*] Res : " + str(res))
          res = eval(res)
        return jsonify(res)
'''

# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE
@api.route('/<string:prod>/timeseries/<string:place>/csv')
class ProductsTimeSeriesByProdAndPlaceByCsv(Resource):
    @api.doc(summary="Get timeseries as CSV", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "CSV returned successfully"})
    def get(self, prod, place):
        """
        Return the time-series payload rendered as a CSV download.

        Example:
        `GET /products/wrf5/timeseries/ca001/csv`
        """

        res = get_resource(request, app.cache, app.use_pymemcache)
        res = None
        
        # Check Memcache
        if res is None:

            
            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            # Check Diskcache
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


                # Save on Diskcache
                app.diskcache.set(request, res, 'csv')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])

        else:
          res = load_cached_json(res, res)

        return csvfy(res)


'''
# TESTED AND WORKING -- USE MEMCACHE -- OLD VERSION
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
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
          res = eval(res)

        return csvfy(res)
'''

'''
# ORIGINAL : Internal Server Error -- USE MEMCACHE 
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
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        return jsonify(res)
'''        

# USE MEMCACHE
@api.route('/<prod>/forecast/<place>/map/image')
class ProductsForecastMapByProdAndPlace(Resource):
    @api.doc(summary="Get the legacy forecast map image endpoint", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "PNG image returned successfully"})
    def get(self,prod,place ):
        """
        Return the legacy forecast map image endpoint for older clients.

        Example:
        `GET /products/ww33/forecast/ca001/map/image`
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
            set_resource(request,res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = load_cached_json(res, {})
                        
        response = make_response(base64.b64decode(res['map']))
        response.headers['Content-Type'] = 'image/png'
        return response



@api.route('/resource/forecast/<string:icon>')
class ProductsForecastIconsPng(Resource):
    @api.doc(summary="Get a static forecast icon", params={"icon": "Static icon filename"}, responses={200: "Icon returned successfully", 404: "Icon not found"})
    def get(self, icon):
        """
        Return one of the static forecast icons bundled with the API.

        Example:
        `GET /products/resource/forecast/sunny.png`
        """
        base_path = f"./static/images/"
        try:
            return send_from_directory(base_path, icon)
        except FileNotFoundError:
            return "Image not found", 404
