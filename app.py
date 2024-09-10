import logging
from flask import Flask
from flask_cors import CORS
from apis import api
from pymemcache.client.base import Client
import memcache.errors
from core.MeteoServices import MeteoServices
from core.GribServices import GribServices
from core.Tiles import Tiles


log = logging.getLogger(__name__)
hdlr = logging.FileHandler('var/log/test.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr)
log.setLevel(logging.INFO)

log.info("start application")

application = Flask(__name__)
CORS(application)
api.init_app(application)

application.config.from_object(__name__)
application.config.from_envvar('APP_SETTINGS', silent=False)

# ------------------ Diskcached --------------------------
use_disk_cached = False

# ------------------ Pymemcache / Memcache ---------------
cache = None
use_pymemcache = False
try:
    cache = Client('memcached:11211')
    # cache = Client([('172.18.0.10', 11211)])
    use_pymemcache = True
except memcache.errors.MemcacheError as memcache_error:
    logging.error("[*]Memcached Error : " + str(memcache_error))

meteo_services = MeteoServices(application.config)
grib_services = GribServices(application.config)
tiles = Tiles(application.config)

