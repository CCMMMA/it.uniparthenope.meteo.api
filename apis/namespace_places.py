import json

import pymemcache
import pymongo
from flask_restx import Namespace, Resource
from core.GetParams import get_params
from core.Places import Places
from flask import request, jsonify
from core.MemcachedMethodHandlers import get_resource, set_resource
import app
from core.Logger import logger

api = Namespace('places', description='Palces API')



@api.route('')
class GetAllPlaces(Resource):
    @api.doc()
    def get(self):

        res = get_resource(request, app.cache, app.use_pymemcache)

        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            if res is None:

                place = Places(app.application.config)
                res = place.get_all_places("places")

                for obj in res:
                    obj.pop("_id")        
            

                app.diskcache.set(request, res, 'json')

                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])

        return res



# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE
@api.route('/search/byname/<string:name>')
class PlacesSearchByName(Resource):
    @api.doc()
    def get(self, name):
        """Returns place information you are looking for.
        :example: /places/search/byname/Napoli
        :param name: Place common name.
        :type name: str.
        :returns: json -- the return josn.
        ------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        
        # Check Memcache
        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)
            
            # Check Diskcache
            if res is None:
                name = name.replace("+", " ")
                params = get_params({'name': name, 'filter': None, 'prod': None, 'limit': None})
                places = Places(app.application.config)
                res = places.get_places_by_name(name, params)

                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])

        else:
            res = eval(res)
        return jsonify(res)

'''
# OLD VERSION
@api.route('/search/byname/<string:name>')
class PlacesSearchByName(Resource):
    @api.doc()
    def get(self, name):
        """Returns place information you are looking for.
        :example: /places/search/byname/Napoli
        :param name: Place common name.
        :type name: str.
        :returns: json -- the return josn.
        ------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            name = name.replace("+", " ")
            params = get_params({'name': name, 'filter': None, 'prod': None, 'limit': None})
            places = Places(app.application.config)
            res = places.get_places_by_name(name, params)
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)
'''

# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('/search/byname/autocomplete')
class PlacesSearchByNameAutocomplete(Resource):
    @api.doc()
    def get(self):
        """Returns ......................
        :example: /places/search/byname/autocomplete
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)

        # Check Memcache
        if res is None:
            
            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            # Check Diskcache
            if res is None:

                places = Places(app.application.config)
                params = get_params({'term': None})
                # params = getParams({'pretty':False})
                opt = {'filter': ['com', 'porti', 'prov', 'reg', "ca", "iim", "med", 'UNI', 'VET', 'VEB'], 'limit': 20}
                res = places.get_places_by_name(params['term'], opt)
                ret_val = []
                for p in res:
                    # ret_val.append({'label': p['long_name']['it'], 'id': p['id'], 'cLon': p['cLon'], 'cLat': p['cLat']})
                    ret_val.append({'label': p['long_name']['it'], 'id': p['id']})
                # res = json.dumps(retVal)
                res = ret_val

                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)

'''
# OLD VERSION
@api.route('/search/byname/autocomplete')
class PlacesSearchByNameAutocomplete(Resource):
    @api.doc()
    def get(self):
        """Returns ......................
        :example: /places/search/byname/autocomplete
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            places = Places(app.application.config)
            params = get_params({'term': None})
            # params = getParams({'pretty':False})
            opt = {'filter': ['com', 'porti', 'prov', 'reg', "ca", "iim", "med", 'UNI', 'VET', 'VEB'], 'limit': 20}
            res = places.get_places_by_name(params['term'], opt)
            ret_val = []
            for p in res:
                # ret_val.append({'label': p['long_name']['it'], 'id': p['id'], 'cLon': p['cLon'], 'cLat': p['cLat']})
                ret_val.append({'label': p['long_name']['it'], 'id': p['id']})
            # res = json.dumps(retVal)
            res = ret_val
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)
'''

# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('/<string:identifier>')
class PlacesByIdentifier(Resource):
    @api.doc()
    def get(self, identifier):
        """Returns the place information you are looking for.
        :example: /places/byid/ca001
        :param identifier: ....
        :type identifier: str.
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)

        # Check Memcache
        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            # Check Diskcache
            if res is None:

                params = get_params({'id': identifier, 'filter': None, 'prod': None})
                places = Places(app.application.config)
                res = places.get_place_by_id(identifier, params)
                if res is None:
                    return jsonify({"details": "Place not found.", "result": "error"})

                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)

'''
# OLD VERSION
@api.route('/<string:identifier>')
class PlacesByIdentifier(Resource):
    @api.doc()
    def get(self, identifier):
        """Returns the place information you are looking for.
        :example: /places/byid/ca001
        :param identifier: ....
        :type identifier: str.
        :returns: json -- the return josn.
        -------------------------------------------------------------------------------------------
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({'id': identifier, 'filter': None, 'prod': None})
            places = Places(app.application.config)
            res = places.get_place_by_id(identifier, params)
            if res is None:
                return jsonify({"details": "Place not found.", "result": "error"})
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)
'''

# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('/search/bycoords/<float:latitude>/<float:longitude>')
class PlacesSearchByCoords(Resource):
    @api.doc()
    def get(self, latitude, longitude):
        """
        :example: /places/search/bycoords/40.78783/14.352
        :param latitude: The latitude.
        :param longitude: The longitude.
        :returns: json -- the return JSON.
        """
        res = get_resource(request, app.cache, app.use_pymemcache)

        # Check Memcache
        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            # Check Diskcache
            if res is None:
                params = get_params({'range': None, 'filter': None, 'prod': None, 'limit': None})
                places = Places(app.application.config)
                res = places.get_places_by_ll(float(longitude), float(latitude), params)
                
                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)

'''
# OLD VERSION
@api.route('/search/bycoords/<float:latitude>/<float:longitude>')
class PlacesSearchByCoords(Resource):
    @api.doc()
    def get(self, latitude, longitude):
        """
        :example: /places/search/bycoords/40.78783/14.352
        :param latitude: The latitude.
        :param longitude: The longitude.
        :returns: json -- the return JSON.
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({'range': None, 'filter': None, 'prod': None, 'limit': None})
            places = Places(app.application.config)
            res = places.get_places_by_ll(float(longitude), float(latitude), params)
            set_resource(request, res, app.cache, app.use_pymemcache, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)
'''

# TESTED AND WORKING -- USE MEMCACHE AND DISKCACHE 
@api.route('/search/byboundingbox/<float:minLatitude>/<float:minLongitude>/<float:maxLatitude>/<float:maxLongitude>')
class PlacesSearchByBoundingBox(Resource):
    @api.doc()
    def get(self, minLatitude, minLongitude, maxLatitude, maxLongitude):
        """
        :example: /places/search/byboundingbox/40.78/14.35/41.22/16.87
        :param minLatitude:  min latitude
        :param minLongitude: min longitude
        :param maxLatitude: max latitude
        :param maxLongitude: min longitude
        :returns: json -- the return JSON.
        """
        res = get_resource(request, app.cache, app.use_pymemcache)

        # Check Memcache
        if res is None:

            res = app.diskcache.get(request, app.diskcache_ttl, app.use_disk_cached)

            # Check Diskcache
            if res is None:
                params = get_params({'filter': None, 'diag': None, 'zoom': None})
                places = Places(app.application.config)
                res = places.get_places_by_bb(float(minLongitude), float(minLatitude), float(maxLongitude),
                                            float(maxLatitude), params)
                # print "------------------------->Result:"+str(res)

                # Save on Diskcache
                app.diskcache.set(request, res, 'json')

                # Save on Memcache
                set_resource(request, res, app.cache, app.application.config, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)

'''
# OLD VERSION
@api.route('/search/byboundingbox/<float:minLatitude>/<float:minLongitude>/<float:maxLatitude>/<float:maxLongitude>')
class PlacesSearchByBoundingBox(Resource):
    @api.doc()
    def get(self, minLatitude, minLongitude, maxLatitude, maxLongitude):
        """
        :example: /places/search/byboundingbox/40.78/14.35/41.22/16.87
        :param minLatitude:  min latitude
        :param minLongitude: min longitude
        :param maxLatitude: max latitude
        :param maxLongitude: min longitude
        :returns: json -- the return JSON.
        """
        res = get_resource(request, app.cache, app.use_pymemcache)
        if res is None:
            params = get_params({'filter': None, 'diag': None, 'zoom': None})
            places = Places(app.application.config)
            res = places.get_places_by_bb(float(minLongitude), float(minLatitude), float(maxLongitude),
                                          float(maxLatitude), params)
            # print "------------------------->Result:"+str(res)
            set_resource(request, res, app.cache, app.application.config, app.application.config['TTL_MEMCACHED'])
        else:
            res = eval(res)
        return jsonify(res)
    '''
