"""Memcached helpers for serializing and retrieving cached resources."""

#################################################
#
# Author: Dario Caramiello
#
#################################################

from time import strftime, gmtime
import hashlib  # hash function for 128bit encryption
import memcache
import json
import os
import pickle
import datetime
from core.Logger import logger

def _decode_cached_value(value):
    """Normalize cached byte payloads into Python strings when possible."""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return value


def load_cached_json(value, fallback=None):
    """Decode a cached JSON payload while preserving a fallback value on failure."""
    value = _decode_cached_value(value)
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError) as exc:
        logger.error("Unable to decode cached JSON payload: %s", exc)
        return fallback


# request the resource from the cache
def get_resource(request_in, cache, use_pymemcache):
    """Fetch a resource from memcached and normalize its representation."""
    if use_pymemcache is False:
        return None

    res_out = None
    m = hashlib.md5(request_in.url.encode('utf-8'))
    if m is not None:
        try:
            res_out = cache.get(m.hexdigest())
            res_out = _decode_cached_value(res_out)

        except memcache.MemcacheError as e:
            logger.error(str(e))
    return res_out


# set resource to cache
def set_resource(request_in, res, cache, use_pymemcache, ttl):
    """Serialize and store a resource in memcached."""
    if use_pymemcache is False:
        return

    m = hashlib.md5(request_in.url.encode('utf-8'))
    if m is not None:
        # to_be_cached = False
        try:
            if isinstance(res, (dict, list)):
                res = json.dumps(res).encode('utf-8')
            cache.set(m.hexdigest(), res, ttl)

        except memcache.MemcacheError as e:
            logger.error(str(e))
            # print("[*] MemcacheError : " + str(e))

