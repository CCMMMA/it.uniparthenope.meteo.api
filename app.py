"""Application bootstrap for the meteorological API service."""

import os

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
from core.RequestPopularityTracker import RequestPopularityTracker

application = Flask(__name__)

# Load deployment settings before extensions are initialized.  Flask-SQLAlchemy
# reads its connection settings during init_app(), so loading APP_SETTINGS later
# made SQLALCHEMY_DATABASE_URI overrides ineffective.
application.config.from_envvar('APP_SETTINGS', silent=False)
application.config.setdefault(
    'SQLALCHEMY_DATABASE_URI',
    os.environ.get('DATABASE_URL', 'postgresql://user:password@postgres:5432/cnmost'),
)
application.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

db.init_app(application)

CORS(application)
api.init_app(application)

# logger.info("Test info log message")
# logger.warning("Test warning log message")
# logger.error("Test error log message")

# ------------------ Diskcached   - Local [ url - local file ] --------------------------
use_disk_cached = True
diskcache = ManageDiskCache(application.config['BASE_DISKCACHE'])
diskcache_ttl = application.config['TTL_DISKCACHE']

# ------------------ Pymemcache / Memcache - [url]-[res] ---------------
cache = None
use_pymemcache = True

try:
    cache = Client(
        application.config.get('MEMCACHED_SERVER', 'memcached:11211'),
        connect_timeout=0.2,
        timeout=0.5,
        no_delay=True,
    )
    # cache = Client([('172.18.0.10', 11211)])
except Exception as memcache_error:
    logger.error("[*]Memcached Error : %s", memcache_error)
    use_pymemcache = False

meteo_services = MeteoServices(application.config)
grib_services = GribServices(application.config)
tiles = Tiles(application.config)
request_popularity_tracker = RequestPopularityTracker(
    application.config.get(
        "REQUEST_POPULARITY_PATH",
        os.path.join(application.config["BASE_DISKCACHE"], "request-popularity.json"),
    ),
    top_limit=application.config.get("POPULAR_REQUESTS_LIMIT", 25),
    flush_every=application.config.get("REQUEST_POPULARITY_FLUSH_EVERY", 100),
    flush_interval_seconds=application.config.get("REQUEST_POPULARITY_FLUSH_INTERVAL", 10.0),
)
