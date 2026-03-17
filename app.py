"""Application bootstrap for the meteorological API service."""

from flask import Flask
from flask_cors import CORS
from apis import api
from pymemcache.client.base import Client
from core.MeteoServices import MeteoServices
from core.GribServices import GribServices
from core.Tiles import Tiles
from core.Logger import logger
from core.ManageDiskCache import ManageDiskCache
from core.Models import db 

application = Flask(__name__)

# TODO: set in ccmmmmaapi.conf
application.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@postgres:5432/cnmost'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(application)

CORS(application)
api.init_app(application)

# logger.info("Test info log message")
# logger.warning("Test warning log message")
# logger.error("Test error log message")

application.config.from_object(__name__)
application.config.from_envvar('APP_SETTINGS', silent=False)

# ------------------ Diskcached   - Local [ url - local file ] --------------------------
use_disk_cached = True
diskcache = ManageDiskCache(application.config['BASE_DISKCACHE'])
diskcache_ttl = application.config['TTL_DISKCACHE']

# ------------------ Pymemcache / Memcache - [url]-[res] ---------------
cache = None
use_pymemcache = True

try:
    cache = Client('memcached:11211')
    # cache = Client([('172.18.0.10', 11211)])
except Exception as memcache_error:
    logger.error("[*]Memcached Error : %s", memcache_error)
    use_pymemcache = False

meteo_services = MeteoServices(application.config)
grib_services = GribServices(application.config)
tiles = Tiles(application.config)
