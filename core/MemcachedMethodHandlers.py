from time import strftime, gmtime
import hashlib  # hash function for 128bit encryption
import memcache
import json
import os
import pickle
import datetime
from core.Logger import logger

# request the resource from the cache
def get_resource(request_in, cache, use_pymemcache):
    if use_pymemcache is False:
        return None

    res_out = None
    m = hashlib.md5(request_in.url.encode('utf-8'))
    if m is not None:
        try:
            res_out = cache.get(m.hexdigest())
            if res_out is not None:
                  res_out = res_out.decode('utf-8')

        except memcache.MemcacheError as e:
            logger.error(str(e))
    return res_out


# set resource to cache
def set_resource(request_in, res, cache, use_pymemcache, ttl):
    if use_pymemcache is False:
        return

    m = hashlib.md5(request_in.url.encode('utf-8'))
    if m is not None:
        # to_be_cached = False
        try:
            if isinstance(res, dict):
              res = json.dumps(res).encode('utf-8')
            cache.set(m.hexdigest(), res, ttl)

        except memcache.MemcacheError as e:
            logger.error(str(e))
            # print("[*] MemcacheError : " + str(e))


