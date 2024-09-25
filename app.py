import logging
import memcache.errors
from flask import Flask
from flask_cors import CORS
from apis import api
from pymemcache.client.base import Client
from core.MeteoServices import MeteoServices
from core.GribServices import GribServices
from core.Tiles import Tiles
from logging.config import dictConfig

########################## Logging #################################

dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(levelname)s: %(message)s',
        },
        'info_format': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s (function [ %(funcName)s ]) (line [ %(lineno)d ]): %(message)s ',
            # 'format': '[%(asctime)s] %(levelname)s in %(module)s (%(funcName)s): %(message)s',
        },
        'error_format': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s (function [ %(funcName)s ]) (line [ %(lineno)d ]): %(message)s ',
        },
        'warning_format': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s (function [ %(funcName)s ]) (line [ %(lineno)d ]): %(message)s ',
        },
        "critical_format": {
            'format': '[%(asctime)s] %(levelname)s in %(module)s (function [ %(funcName)s ]) (line [ %(lineno)d ]): %(message)s '
        }
    },
    'handlers': {
        #'wsgi': {
        #    'class': 'logging.StreamHandler',
        #    'stream': 'ext://flask.logging.wsgi_errors_stream',
        #    'formatter': 'default'
        #},
        'info_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'info_format',
            'level': 'INFO',
        },
        'error_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'error_format',
            'level': 'ERROR',
        },
        'warning_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'warning_format',
            'level': 'WARNING',
        },
        'critical_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'critical_format',
            'level': 'CRITICAL',
        }
    },
    'loggers': {
        'main_logger': {
            'level': 'DEBUG',
            'handlers': ['info_handler', 'error_handler', 'warning_handler', 'critical_handler'],
            'propagate': False
        }
    }
    #'root': {
    #    'level': 'INFO',
    #    'handlers': ['wsgi']
    #}
})

logger = logging.getLogger('main_logger')

####################################################################

application = Flask(__name__)
CORS(application)
api.init_app(application)

logger.info("Test info log message")
logger.warning("Test warning log message")
logger.error("Test error log message")

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
    use_pymemcache = True
except memcache.errors.MemcacheError as memcache_error:
    print("[*]Memcached Error : " + str(memcache_error))
    # logging.error("[*]Memcached Error : " + str(memcache_error))

meteo_services = MeteoServices(application.config)
grib_services = GribServices(application.config)
tiles = Tiles(application.config)

