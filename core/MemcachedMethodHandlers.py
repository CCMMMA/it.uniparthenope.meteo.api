"""Memcached helpers for serializing and retrieving cached resources."""

#################################################
#
# Author: Dario Caramiello
#
#################################################

import hashlib  # hash function for 128bit encryption
import json
from core.Logger import logger


def _cache_key(request_in):
    """Return the stable memcache key derived from the request URL."""
    return hashlib.md5(request_in.url.encode('utf-8')).hexdigest()


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

    try:
        return _decode_cached_value(cache.get(_cache_key(request_in)))
    except Exception as exc:
        logger.error("Unable to read memcache entry: %s", exc)
        return None


# set resource to cache
def set_resource(request_in, res, cache, use_pymemcache, ttl):
    """Serialize and store a resource in memcached."""
    if use_pymemcache is False:
        return

    try:
        if isinstance(res, (dict, list)):
            res = json.dumps(res).encode('utf-8')
        elif isinstance(res, str):
            res = res.encode('utf-8')
        cache.set(_cache_key(request_in), res, ttl)
    except Exception as exc:
        logger.error("Unable to write memcache entry: %s", exc)
