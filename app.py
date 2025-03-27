# import logging
# from logging.config import dictConfig
import memcache.errors
from flask import Flask
from flask_cors import CORS
from apis import api
from pymemcache.client.base import Client
from core.MeteoServices import MeteoServices
from core.GribServices import GribServices
from core.Tiles import Tiles
from core.Logger import logger

application = Flask(__name__)
CORS(application)
api.init_app(application)

# logger.info("Test info log message")
# logger.warning("Test warning log message")
# logger.error("Test error log message")

application.config.from_object(__name__)
application.config.from_envvar('APP_SETTINGS', silent=False)

# ------------------ Diskcached --------------------------
use_disk_cached = True

# ------------------ Pymemcache / Memcache ---------------
cache = None
use_pymemcache = True
try:
    cache = Client('memcached:11211')

    # cache = Client([('172.18.0.10', 11211)])
    # use_pymemcache = True
# except memcache.errors.MemcacheError as memcache_error:
except Execption as memcache_error:
    print("[*]Memcached Error : " + str(memcache_error))
    logging.error("[*]Memcached Error : " + str(memcache_error))
    use_pymemcache = False

meteo_services = MeteoServices(application.config)
grib_services = GribServices(application.config)
tiles = Tiles(application.config)

