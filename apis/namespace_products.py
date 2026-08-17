"""RESTX namespace for forecast products, plots, legends, and time series."""

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

import app
import base64
import os
from types import SimpleNamespace
from flask_restx import Namespace, Resource
from flask import current_app, jsonify, Response, make_response, request, send_from_directory
from datetime import datetime, timedelta, timezone

from core.Logger import logger
from core.GetParams import get_params
from core.MemcachedMethodHandlers import delete_resource, get_resource, set_resource, load_cached_json
from core.MeteoServices import MeteoServices, csvfy
from core.Places import Places
from core.MakeArchivePaths import MakeArchivePaths
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION

api = Namespace('products', description='Forecast products, plots, time series, GRIB exports, legends, and static product assets.')


def _runtime_services():
    """Return composed dependencies for incrementally migrated product handlers."""
    return current_app.extensions[RUNTIME_SERVICES_EXTENSION]


def _cache_request_with_default_date():
    """Build a cache-key request object with a default forecast date when one is omitted."""
    cache_url = request.url
    if "date" not in request.args:
        ncep_date = datetime.now(timezone.utc).strftime("%Y%m%dZ%H00")
        separator = '&' if '?' in cache_url else '?'
        cache_url = f"{cache_url}{separator}date={ncep_date}"
    return SimpleNamespace(url=cache_url)


def _normalized_option_string(raw_opt, ignore_fields=False):
    """Return a stable normalized option string."""
    options = []
    for item in (raw_opt or "").split(","):
        value = item.strip()
        if not value:
            continue
        if ignore_fields and value == "fields":
            continue
        options.append(value)
    return ",".join(sorted(set(options)))


def _effective_forecast_date(timeref=None):
    """Return the effective forecast datetime used by the service layer."""
    meteo_services = _runtime_services().meteo
    return meteo_services._format_datetime_ref(
        meteo_services._parse_datetime_ref(
            timeref, round_to_hour=(timeref is None)
        )
    )


def _effective_timeseries_date(timeref=None):
    """Return the effective timeseries start datetime used by the service layer."""
    meteo_services = _runtime_services().meteo
    return meteo_services._format_datetime_ref(
        meteo_services._parse_datetime_ref(
            timeref, default_midnight=(timeref is None)
        )
    )


def _request_window(date_value=None, hours=None):
    """Return the inclusive start/exclusive end window for maintenance endpoints."""
    start = app.meteo_services._parse_datetime_ref(date_value, default_midnight=(date_value is None))
    duration_hours = int(hours if hours is not None else 168)
    return start, start + timedelta(hours=duration_hours)


def _forecast_cache_key(prod, place, params=None):
    """Build a canonical cache key for forecast payloads."""
    params = params or {}
    return "|".join(
        [
            "products-forecast-v1",
            str(prod),
            str(place),
            _effective_forecast_date(params.get("date")),
            str(params.get("filter") or ""),
            _normalized_option_string(params.get("opt") or ""),
        ]
    )


def _timeseries_cache_key(prod, place, params=None):
    """Build a canonical cache key shared by time-series representations."""
    params = params or {}
    opt = _normalized_option_string(params.get("opt") or "", ignore_fields=True)
    return "|".join(
        [
            "products-timeseries-v1",
            str(prod),
            str(place),
            _effective_timeseries_date(params.get("date")),
            str(int(params.get("step", 1))),
            str(int(params.get("hours", 0))),
            opt,
        ]
    )


def _timeseries_fields(prod):
    """Return the field dictionary used by CSV rendering without recomputing the time series."""
    return _runtime_services().meteo.maps["products"][prod]["fields"]


def _popular_request_params(endpoint, prod, place, params):
    """Return the normalized signature stored by the popularity tracker."""
    if endpoint == "forecast":
        return {
            "date": _effective_forecast_date(params.get("date")),
            "hours": 0,
            "step": 1,
            "opt": _normalized_option_string(params.get("opt") or ""),
            "filter": str(params.get("filter") or ""),
        }

    return {
        "date": _effective_timeseries_date(params.get("date")),
        "hours": int(params.get("hours", 0)),
        "step": int(params.get("step", 1)),
        "opt": _normalized_option_string(params.get("opt") or "", ignore_fields=True),
        "filter": "",
    }


def _record_popular_request(endpoint, prod, place, params):
    """Record one successful forecast or time-series request."""
    _runtime_services().popularity.record(
        endpoint,
        prod,
        place,
        _popular_request_params(endpoint, prod, place, params),
    )


def _top_level_cache_delete(cache_key):
    """Delete one top-level cache entry from memcache and disk cache."""
    deleted_disk = app.diskcache.delete(cache_key_source=cache_key, flag_diskcache=app.use_disk_cached)
    deleted_mem = delete_resource(None, app.cache, app.use_pymemcache, cache_key_override=cache_key)
    return deleted_disk, deleted_mem


def _warm_forecast_cache(prod, place, params):
    """Build and store one forecast payload under the canonical cache key."""
    cache_key = _forecast_cache_key(prod, place, params)
    response = app.meteo_services.modelOutput(params)
    if 'result' in response and "ok" not in response['result']:
        return {"cache_key": cache_key, "status": "skipped", "details": response}

    app.diskcache.set(request=None, res=response, type_file='json', cache_key_source=cache_key)
    set_resource(
        None,
        response,
        app.cache,
        app.use_pymemcache,
        app.application.config['TTL_MEMCACHED'],
        cache_key_override=cache_key,
    )
    return {"cache_key": cache_key, "status": "ok"}


def _warm_timeseries_cache(prod, place, params):
    """Build and store one time-series payload under the canonical cache key."""
    cache_key = _timeseries_cache_key(prod, place, params)
    response = app.meteo_services.timeseries(params)
    if 'result' in response and "ok" not in response['result']:
        return {"cache_key": cache_key, "status": "skipped", "details": response}

    app.diskcache.set(request=None, res=response, type_file='json', cache_key_source=cache_key)
    set_resource(
        None,
        response,
        app.cache,
        app.use_pymemcache,
        app.application.config['TTL_MEMCACHED'],
        cache_key_override=cache_key,
    )
    return {"cache_key": cache_key, "status": "ok"}

# TESTED AND WORKING - NO CACHE USE 
@api.route('')
class Products(Resource):
    """Resource handler for products operations."""
    @api.doc(summary="List products", responses={200: "Product catalog returned successfully"})
    def get(self):
        """
        Return the catalog of available forecast products.

        Example:
        `GET /products`
        """
        res = _runtime_services().meteo.getProds()
        return jsonify(products=res)

# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/<string:place>/avail')
class ProductsAvailable(Resource):
    """Resource handler for products available operations."""
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
        res = _runtime_services().meteo.getProductAvail(params)
        return jsonify(avail=res)


# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/<string:place>/avail/calendar')
class ProductsAvailableCalendar(Resource):
    """Resource handler for products available calendar operations."""
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
        res = _runtime_services().meteo.getProductAvailCalendar(params)
        return jsonify(res)


# TESTED AND WORKING - NO CACHE USE 
@api.route('/maps')
class ProductsMap(Resource):
    """Resource handler for products map operations."""
    @api.doc(summary="Get maps metadata", responses={200: "Maps metadata returned successfully"})
    def get(self):
        """
        Return the map metadata used by product visualizations.

        Example:
        `GET /products/maps`
        """
        res = _runtime_services().meteo.getMaps()
        return jsonify(maps=res)


# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/maps/themes')
class ProductsThemesByProd(Resource):
    """Resource handler for products themes by prod operations."""
    @api.doc(summary="Get themes for a product", params={"prod": "Product code"}, responses={200: "Theme metadata returned successfully"})
    def get(self, prod):
        """
        Return the map themes available for the selected product.

        Example:
        `GET /products/wrf5/maps/themes`
        """
        res = _runtime_services().meteo.getThemes(prod)
        return jsonify(themes=res)


# TESTED AND WORKING - NO CACHE USE
@api.route('/<string:prod>')
class ProductsOutputsByProd(Resource):
    """Resource handler for products outputs by prod operations."""
    @api.doc(summary="Get product metadata", params={"prod": "Product code"}, responses={200: "Product metadata returned successfully"})
    def get(self, prod):
        """
        Return the metadata block for a single product.

        Example:
        `GET /products/wrf5`
        """

        if prod is None or prod == "" or prod == "null":
            prod="wrf5"

        res = _runtime_services().meteo.getProds(prod)
        return jsonify(outputs=res)


# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/outputs')
class ProductsOutputsByProd(Resource):
    """Resource handler for products outputs by prod operations."""
    @api.doc(summary="List outputs for a product", params={"prod": "Product code"}, responses={200: "Outputs returned successfully"})
    def get(self, prod):
        """
        Return the list of outputs available for the selected product.

        Example:
        `GET /products/wrf5/outputs`
        """
        res = _runtime_services().meteo.getOutputs(prod)
        return jsonify(outputs=res)


# TESTED AND WORKING - NO CACHE USE 
@api.route('/<string:prod>/fields')
class ProductsFieldsByProd(Resource):
    """Resource handler for products fields by prod operations."""
    @api.doc(summary="List fields for a product", params={"prod": "Product code"}, responses={200: "Field metadata returned successfully"})
    def get(self, prod):
        """
        Return the fields that can be queried for the selected product.

        Example:
        `GET /products/wrf5/fields`
        """
        res = _runtime_services().meteo.getFields(prod)
        return jsonify(fields=res)

# TESTED AND WORKING - USE MEMCACHE AND DISKCACHE 
@api.route('/<string:prod>/forecast/<string:place>')
class ProductsForecastByProdAndPlace(Resource):
    """Resource handler for products forecast by prod and place operations."""
    @api.doc(summary="Get forecast data for a product and place", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Forecast returned successfully", 404: "Forecast not available"})
    def get(self, prod, place):
        """
        Return the structured forecast payload for the selected product and place.

        Example:
        `GET /products/wrf5/forecast/com63049`
        """
        params = get_params({
            'place': place,
            'filter': None,
            'prod': prod,
            'date': None,
            'opt': ""
        })
        cache_key = _forecast_cache_key(prod, place, params)
        services = _runtime_services()
        res = get_resource(
            request,
            services.memory_cache,
            services.memory_cache_enabled,
            cache_key_override=cache_key,
        )

        # Check Memcache
        if res is None:
            res = services.disk_cache.get(
                request,
                services.disk_cache_ttl,
                services.disk_cache_enabled,
                cache_key_source=cache_key,
            )

            # Check Diskcache 
            if res is None:    
                res = services.meteo.modelOutput(params)

                if 'result' in res and "ok" not in res['result']:
                    return jsonify(res)

                
                # Save on Diskcache
                services.disk_cache.set(
                    request, res, 'json', cache_key_source=cache_key
                )

                # Save on Memcache
                set_resource(
                    request,
                    res,
                    services.memory_cache,
                    services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                    cache_key_override=cache_key,
                )

        payload = load_cached_json(res, res)
        if payload and payload.get("result") == "ok":
            _record_popular_request("forecast", prod, place, params)
        return jsonify(payload)

# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE
@api.route('/<string:prod>/forecast/<string:place>/plot/image')
class ProductsForecastMapByProdAndPlace(Resource):
    """Resource handler for products forecast map by prod and place operations."""
    @api.doc(summary="Get rendered forecast plot image", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "PNG image returned successfully"})
    def get(self, prod, place):
        """
        Return a rendered PNG plot for the selected product and place.

        Example:
        `GET /products/ww33/forecast/ca001/plot/image`
        """

        services = _runtime_services()
        cache_request = _cache_request_with_default_date()
        
        # Check Memecache
        res = get_resource(
            cache_request, services.memory_cache, services.memory_cache_enabled
        )

        if res is None:

            res2 = services.disk_cache.get(
                cache_request,
                services.disk_cache_ttl,
                flag_diskcache=services.disk_cache_enabled,
            )

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
                
                (mapData, imageName) = services.meteo.ModelPlotImage(
                    services.disk_cache_enabled, params
                )
            
                res = {
                    'plot': base64.b64encode(mapData).decode('utf-8'),
                    # 'plot': mapData,
                    'imageName': imageName
                }
                
                # Save on Diskcache
                services.disk_cache.set(
                    cache_request,
                    base64.b64encode(mapData).decode('utf-8'),
                    'plot',
                    flag_diskcache=services.disk_cache_enabled,
                )

                # Save on Memcache 
                set_resource(
                    cache_request,
                    res,
                    services.memory_cache,
                    services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                )
            
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

# @api.route('/wrf5/forecast/<string:place>/<float:lat>/<float:lon>/plot/SkewT/image')
@api.route('/wrf5/forecast/plot/SkewT/image')
class ProductSkewTByProdAndPlace(Resource):
    """Resource handler for product skew tby prod and place operations."""
    @api.doc(summary="Get a Skew-T plot image", params={"date": "Optional forecast reference time as query parameter"}, responses={200: "Skew-T image returned successfully"})
    def get(self):
        """
        Return a Skew-T diagnostic plot as a PNG image.

        Examples:
        `GET /products/wrf5/forecast/plot/SkewT/image`
        `GET /products/wrf5/forecast/plot/SkewT/image?date=20250915Z1000`
        """
     
        services = _runtime_services()
        cache_request = _cache_request_with_default_date()
        
        res = get_resource(
            cache_request, services.memory_cache, services.memory_cache_enabled
        )

        if res is None:
            
            params = get_params({
                'prod': "wrf5",
                'lat': 40.856,
                'lon': 14.352,
                'date': None,
            })

            (mapData, imageName) = services.meteo.ModelPlotSkewT(
                services.disk_cache_enabled, params
            )

            res = {
                'plot': base64.b64encode(mapData).decode('utf-8'),
                # 'plot': mapData,
                'imageName': imageName
            }

            set_resource(
                cache_request,
                res,
                services.memory_cache,
                services.memory_cache_enabled,
                current_app.config['TTL_MEMCACHED'],
            )
  
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
    """Resource handler for products forecast plot and alt operations."""
    @api.doc(summary="Get plot alternative text payload", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Alternative text payload returned successfully"})
    def get(self, prod, place, language="en-US"):
        """
        Return an alternative-text style description payload for a generated plot.

        Example:
        `GET /products/wrf5/forecast/com63049/plot/alt`
        """
        services = _runtime_services()
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

        all_info_place = Places(current_app.config).get_place_by_id(place)
        long_name = all_info_place['long_name']['it']
        res = services.meteo.MakeJsonAlt(prod, long_name, params)

        return res


# TESTED AND WORKING -- USE MEMCACHE 
@api.route('/<string:prod>/forecast/<string:domain>/grib/text')
class ProductsForecastGribJsonByProdAndDomain(Resource):
    """Resource handler for products forecast grib json by prod and domain operations."""
    @api.doc(summary="Get GRIB-oriented text export", params={"prod": "Product code", "domain": "Forecast domain code"}, responses={200: "Text export returned successfully"})
    def get(self, prod, domain):
        """
        Return a text export derived from GRIB-oriented product data.

        Example:
        `GET /products/wrf5/forecast/d02/grib/text`
        """
        services = _runtime_services()
        res = get_resource(
            request, services.memory_cache, services.memory_cache_enabled
        )
        if res is None:
            params = get_params({
                'domain': domain,
                'prod': prod,
                'date': None,
                'opt': ""
            })
            json_data = services.grib.asText(params)
            res = json_data
            set_resource(
                request,
                res,
                services.memory_cache,
                services.memory_cache_enabled,
                current_app.config['TTL_MEMCACHED'],
            )
        
        logger.debug("/grib/text response ready: %s bytes", len(res) if res is not None else 0)
        return Response(res, mimetype='text/plain')


# ERROR -- USE MEMCACHE 
@api.route('/<string:prod>/forecast/<string:domain>/grib/json')
class ProductsForecastGribJsonByProdAndDomain(Resource):
    """Resource handler for products forecast grib json by prod and domain operations."""
    @api.doc(summary="Get GRIB-oriented JSON export", params={"prod": "Product code", "domain": "Forecast domain code"}, responses={200: "JSON export returned successfully"})
    def get(self, prod, domain):
        """
        Return a JSON export derived from GRIB-oriented product data.

        Example:
        `GET /products/wrf5/forecast/d02/grib/json`
        """
        services = _runtime_services()
        res = get_resource(
            request, services.memory_cache, services.memory_cache_enabled
        )
        if res is None:
            params = get_params({
                'domain': domain,
                'prod': prod,
                'date': None,
                'opt': ""
            })
            json_data = services.grib.asJson(params)
            res = json_data
            set_resource(
                request,
                res,
                services.memory_cache,
                services.memory_cache_enabled,
                current_app.config['TTL_MEMCACHED'],
            )
        return jsonify(res)


# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('/<string:prod>/forecast/<string:place>/plot')
class ProductsForecastMapByProdAndPlace(Resource):
    """Resource handler for products forecast map by prod and place operations."""
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
    """Resource handler for products forecast bar by prod and position and output operations."""
    @api.doc(summary="Get a legend image", params={"prod": "Product code", "position": "Legend position", "output": "Output code"}, responses={200: "Legend image returned successfully"})
    def get(self, prod, position, output):
        """
        Return a legend image for the selected product output.

        Example:
        `GET /products/ww33/forecast/legend/right/waveheight`
        """
        services = _runtime_services()
        res = get_resource(
            request, services.memory_cache, services.memory_cache_enabled
        )
        if res is None:
            params = get_params({
                'width': None,
                'height': None,
                'date': None
            })
            bar_data = services.meteo.getlegenddata(prod, position, output, params)
            res = {
                'legend': base64.b64encode(bar_data).decode('utf-8')
            }
            set_resource(
                request,
                res,
                services.memory_cache,
                services.memory_cache_enabled,
                current_app.config['TTL_MEMCACHED'],
            )
        else:
          res = load_cached_json(res, {})

        response = make_response(base64.b64decode(res['legend']))
        response.headers['Content-Type'] = 'image/png'

        return response


# ORIGINAL : Internal Server Error -- USE MEMCACHE 
@api.route('/<string:prod>/forecast/legend/<string:position>/<string:output>/ncwms')
class ProductsForecastBarByProdAndPositionAndOutputFromNcWMS(Resource):
    """Resource handler for products forecast bar by prod and position and output from nc wms operations."""
    @api.doc(summary="Get a legend image through ncWMS-related generation", params={"prod": "Product code", "position": "Legend position", "output": "Output code"}, responses={200: "Legend image returned successfully"})
    def get(self, prod, position, output):
        """
        Return a legend image generated through the ncWMS-oriented path.

        Example:
        `GET /products/ww33/forecast/legend/right/waveheight/ncwms`
        """
        services = _runtime_services()
        res = get_resource(
            request, services.memory_cache, services.memory_cache_enabled
        )
        if res is None:
            params = get_params({
                'width': None,
                'height': None,
                'date': None
            })
            bar_data = services.meteo.getlegenddata1(
                prod, position, output, params
            )
            res = {
                'legend': base64.b64encode(bar_data).decode('utf-8')
            }
            set_resource(
                request,
                res,
                services.memory_cache,
                services.memory_cache_enabled,
                current_app.config['TTL_MEMCACHED'],
            )
        else:
          res = load_cached_json(res, {})

        response = make_response(base64.b64decode(res['legend']))
        response.headers['Content-Type'] = 'image/png'

        return response


@api.route('/<string:prod>/plot/<string:output>/metacharts')
class ProductsPlotMetacharts(Resource):
    """Resource handler for products plot metacharts operations."""
    @api.doc(summary="Get plot metadata charts", params={"prod": "Product code", "output": "Output code"}, responses={200: "Metacharts payload returned successfully"})
    def get(self, prod, output):
        """
        Return plotting metadata used by downstream frontend chart rendering.

        Example:
        `GET /products/wrf5/plot/gen/metacharts`
        """
        services = _runtime_services()
        res = get_resource(
            request, services.memory_cache, services.memory_cache_enabled
        )
       
        if res is None:

            res = services.disk_cache.get(
                request,
                services.disk_cache_ttl,
                flag_diskcache=services.disk_cache_enabled,
            )
      
            if res is None:
                
                meta_charts = services.meteo.plotmetacharts(prod, output)

                res = meta_charts

                services.disk_cache.set(
                    request,
                    res,
                    'json',
                    flag_diskcache=services.disk_cache_enabled,
                )

            # Promote both newly generated values and disk hits into memory.
            set_resource(
                request,
                res,
                services.memory_cache,
                services.memory_cache_enabled,
                current_app.config['TTL_MEMCACHED'],
            )
                
        else:
            res = load_cached_json(res, {})
        return jsonify(res)


# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('/<string:prod>/timeseries/<string:place>')
class ProductsTimeseriesByProdAndPlace(Resource):
    """Resource handler for products timeseries by prod and place operations."""
    @api.doc(summary="Get timeseries data", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "Timeseries returned successfully"})
    def get(self, prod, place):
        """
        Return the structured time-series payload for the selected product and place.

        Example:
        `GET /products/ww33/timeseries/ca001`
        """

        # Check Memcache
        base_params = {
            'place': place,
            'prod': prod,
            'output': None,
            'hours': 0,
            'step': 1,
            'md5': None,
            'date': None,
            'opt': ""
        }
        cache_key = _timeseries_cache_key(prod, place, base_params)
        services = _runtime_services()
        res = get_resource(
            request,
            services.memory_cache,
            services.memory_cache_enabled,
            cache_key_override=cache_key,
        )

        if res is None:

            params = get_params({
                'place': place,
                'prod': prod,
                'date': None
            })

            path_archive_file = MakeArchivePaths.makePath(
                params['prod'], params['place'], config=current_app.config
            )
            # Check Diskcache
            res = services.disk_cache.get(
                request,
                services.disk_cache_ttl,
                path_archive_file,
                services.disk_cache_enabled,
                cache_key_source=cache_key,
            )
            
            if res is None:
                params = get_params(base_params)
                time_series_data = services.meteo.timeseries(params)

                if 'result' in time_series_data and "ok" not in time_series_data['result']:
                    return jsonify(time_series_data)

                res = time_series_data

                # Save on Diskcache
                services.disk_cache.set(
                    request, res, 'json', cache_key_source=cache_key
                )

                # Save on Memcache
                set_resource(
                    request,
                    res,
                    services.memory_cache,
                    services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                    cache_key_override=cache_key,
                )

        else:
            res = load_cached_json(res, {})
        if res and res.get("result") == "ok":
            _record_popular_request("timeseries", prod, place, base_params)
        return jsonify(res)


# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE
@api.route('/<string:prod>/timeseries/<string:place>/csv')
class ProductsTimeSeriesByProdAndPlaceByCsv(Resource):
    """Resource handler for products time series by prod and place by csv operations."""
    @api.doc(summary="Get timeseries as CSV", params={"prod": "Product code", "place": "Place identifier"}, responses={200: "CSV returned successfully"})
    def get(self, prod, place):
        """
        Return the time-series payload rendered as a CSV download.

        Example:
        `GET /products/wrf5/timeseries/ca001/csv`
        """

        params = get_params({
            'place': place,
            'prod': prod,
            'hours': 0,
            'step': 1,
            'md5': None,
            'date': None,
            'opt': "fields"
        })
        cache_key = _timeseries_cache_key(prod, place, params)
        services = _runtime_services()
        res = get_resource(
            request,
            services.memory_cache,
            services.memory_cache_enabled,
            cache_key_override=cache_key,
        )
        
        # Check Memcache
        if res is None:

            archive_params = get_params({
                'place': place,
                'prod': prod,
                'date': None
            })
            path_archive_file = MakeArchivePaths.makePath(
                archive_params['prod'],
                archive_params['place'],
                config=current_app.config,
            )
            res = services.disk_cache.get(
                request,
                services.disk_cache_ttl,
                path_archive_file,
                services.disk_cache_enabled,
                cache_key_source=cache_key,
            )

            # Check Diskcache
            if res is None:
                time_series_data = services.meteo.timeseries(params)

                if 'result' in time_series_data and "ok" not in time_series_data['result']:
                    return jsonify(time_series_data)

                res = time_series_data


                # Save on Diskcache
                services.disk_cache.set(
                    request, res, 'json', cache_key_source=cache_key
                )

                # Save on Memcache
                set_resource(
                    request,
                    res,
                    services.memory_cache,
                    services.memory_cache_enabled,
                    current_app.config['TTL_MEMCACHED'],
                    cache_key_override=cache_key,
                )

        else:
          res = load_cached_json(res, res)

        csv_payload = dict(res)
        if "fields" not in csv_payload:
            csv_payload["fields"] = _timeseries_fields(prod)

        if res and res.get("result") == "ok":
            _record_popular_request("timeseries", prod, place, params)

        return csvfy(csv_payload)


@api.route('/<string:prod>/invalidate/<string:place>/')
class ProductsInvalidateByProdAndPlace(Resource):
    """Resource handler for targeted cache invalidation by product and place."""

    @api.doc(
        summary="Invalidate forecast and time-series caches for a product/place window",
        params={
            "prod": "Product code",
            "place": "Place identifier",
            "date": "Optional window start as YYYYMMDDZhhmm, defaults to current UTC day at 00:00",
            "hours": "Window length in hours, defaults to 168",
        },
        responses={200: "Cache entries invalidated successfully"},
    )
    def get(self, prod, place):
        """Invalidate per-hour, forecast, and time-series caches for one product/place window."""
        start, end = _request_window(request.args.get("date"), request.args.get("hours"))
        hours = int(request.args.get("hours", 168))

        deleted_model_output = 0
        current = start
        while current < end:
            cache_path = app.meteo_services._model_output_cache_path(prod, place, current.strftime("%Y%m%dZ%H%M"))
            if os.path.isfile(cache_path):
                os.remove(cache_path)
                deleted_model_output += 1
            current += timedelta(hours=1)

        deleted_top_level_disk = 0
        deleted_top_level_mem = 0
        matched_requests = []

        for record in app.request_popularity_tracker.matching_requests(prod=prod, place=place):
            params = record["params"]
            record_start = app.meteo_services._parse_datetime_ref(params["date"])
            record_end = record_start + timedelta(hours=max(1, int(params.get("hours", 0) or 0)))
            if record_end <= start or record_start >= end:
                continue

            matched_requests.append(record)
            if record["endpoint"] == "forecast":
                cache_key = _forecast_cache_key(prod, place, params)
            else:
                cache_key = _timeseries_cache_key(prod, place, params)
            deleted_disk, deleted_mem = _top_level_cache_delete(cache_key)
            deleted_top_level_disk += deleted_disk
            deleted_top_level_mem += int(bool(deleted_mem))

        return jsonify(
            {
                "result": "ok",
                "prod": prod,
                "place": place,
                "date": start.strftime("%Y%m%dZ%H%M"),
                "hours": hours,
                "deleted_model_output_files": deleted_model_output,
                "deleted_top_level_disk_entries": deleted_top_level_disk,
                "deleted_top_level_memcache_entries": deleted_top_level_mem,
                "matched_popular_requests": len(matched_requests),
            }
        )


@api.route('/<string:prod>/rebuild/')
class ProductsRebuildByProd(Resource):
    """Resource handler for targeted cache rebuild by product."""

    @api.doc(
        summary="Rebuild forecast and time-series caches for the most popular requests of a product",
        params={
            "prod": "Product code",
            "date": "Optional window start as YYYYMMDDZhhmm, defaults to current UTC day at 00:00",
            "hours": "Window length in hours, defaults to 168",
            "limit": "Optional popularity cap, defaults to POPULAR_REQUESTS_LIMIT",
        },
        responses={200: "Popular caches rebuilt successfully"},
    )
    def get(self, prod):
        """Rebuild caches for the most popular forecast and time-series signatures of one product."""
        start, _ = _request_window(request.args.get("date"), request.args.get("hours"))
        hours = int(request.args.get("hours", 168))
        limit = int(request.args.get("limit", app.application.config.get("POPULAR_REQUESTS_LIMIT", 25)))
        start_ref = start.strftime("%Y%m%dZ%H%M")

        forecast_records = app.request_popularity_tracker.top_requests(prod=prod, endpoint="forecast", limit=limit)
        timeseries_records = app.request_popularity_tracker.top_requests(prod=prod, endpoint="timeseries", limit=limit)

        forecast_results = []
        for record in forecast_records:
            for offset in range(hours):
                dt_ref = (start + timedelta(hours=offset)).strftime("%Y%m%dZ%H%M")
                params = {
                    "place": record["place"],
                    "filter": record["params"].get("filter") or None,
                    "prod": prod,
                    "date": dt_ref,
                    "opt": record["params"].get("opt") or "",
                }
                forecast_results.append(_warm_forecast_cache(prod, record["place"], params))

        timeseries_results = []
        for record in timeseries_records:
            params = {
                "place": record["place"],
                "prod": prod,
                "output": None,
                "hours": hours,
                "step": int(record["params"].get("step", 1)),
                "md5": None,
                "date": start_ref,
                "opt": record["params"].get("opt") or "",
            }
            timeseries_results.append(_warm_timeseries_cache(prod, record["place"], params))

        return jsonify(
            {
                "result": "ok",
                "prod": prod,
                "date": start_ref,
                "hours": hours,
                "popularity_limit": limit,
                "forecast_rebuilt": sum(1 for item in forecast_results if item["status"] == "ok"),
                "timeseries_rebuilt": sum(1 for item in timeseries_results if item["status"] == "ok"),
                "forecast_candidates": len(forecast_records),
                "timeseries_candidates": len(timeseries_records),
            }
        )


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
    """Resource handler for products forecast map by prod and place operations."""
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
    """Resource handler for products forecast icons png operations."""
    @api.doc(summary="Get a static forecast icon", params={"icon": "Static icon filename"}, responses={200: "Icon returned successfully", 404: "Icon not found"})
    def get(self, icon):
        """
        Return one of the static forecast icons bundled with the API.

        Example:
        `GET /products/resource/forecast/sunny.png`
        """
        base_path = "./static/images/"
        try:
            return send_from_directory(base_path, icon)
        except FileNotFoundError:
            return "Image not found", 404
