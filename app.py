"""Application bootstrap for the meteorological API service."""

import os

from flask import Flask
from flask_cors import CORS
from apis import api
from apis.versioning import register_version_response_headers
from pymemcache.client.base import Client
from core.MeteoServices import MeteoServices
from core.GribServices import GribServices
from core.Tiles import Tiles
from core.Logger import logger
from core.ManageDiskCache import ManageDiskCache
from core.Models import db
from core.RequestPopularityTracker import RequestPopularityTracker
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION, RuntimeServices


def _create_runtime_services(flask_application: Flask) -> RuntimeServices:
    """Construct reusable adapters and services from validated Flask configuration."""
    memory_cache = None
    memory_cache_enabled = True

    try:
        memory_cache = Client(
            flask_application.config.get("MEMCACHED_SERVER", "memcached:11211"),
            connect_timeout=0.2,
            timeout=0.5,
            no_delay=True,
        )
    except Exception as memcache_error:
        logger.error("[*]Memcached Error : %s", memcache_error)
        memory_cache_enabled = False

    disk_cache_enabled = True
    disk_cache_ttl = flask_application.config["TTL_DISKCACHE"]
    disk_cache = ManageDiskCache(flask_application.config["BASE_DISKCACHE"])
    meteo = MeteoServices(flask_application.config)
    grib = GribServices(flask_application.config)
    tile_service = Tiles(flask_application.config, meteo)
    popularity = RequestPopularityTracker(
        flask_application.config.get(
            "REQUEST_POPULARITY_PATH",
            os.path.join(flask_application.config["BASE_DISKCACHE"], "request-popularity.json"),
        ),
        top_limit=flask_application.config.get("POPULAR_REQUESTS_LIMIT", 25),
        flush_every=flask_application.config.get("REQUEST_POPULARITY_FLUSH_EVERY", 100),
        flush_interval_seconds=flask_application.config.get(
            "REQUEST_POPULARITY_FLUSH_INTERVAL", 10.0
        ),
    )
    return RuntimeServices(
        memory_cache=memory_cache,
        memory_cache_enabled=memory_cache_enabled,
        disk_cache=disk_cache,
        disk_cache_enabled=disk_cache_enabled,
        disk_cache_ttl=disk_cache_ttl,
        meteo=meteo,
        grib=grib,
        tiles=tile_service,
        popularity=popularity,
    )


def _publish_legacy_globals(
    flask_application: Flask, services: RuntimeServices
) -> None:
    """Keep existing handlers operational while they migrate to app extensions."""
    global application
    global cache, use_pymemcache
    global diskcache, use_disk_cached, diskcache_ttl
    global meteo_services, grib_services, tiles, request_popularity_tracker

    application = flask_application
    cache = services.memory_cache
    use_pymemcache = services.memory_cache_enabled
    diskcache = services.disk_cache
    use_disk_cached = services.disk_cache_enabled
    diskcache_ttl = services.disk_cache_ttl
    meteo_services = services.meteo
    grib_services = services.grib
    tiles = services.tiles
    request_popularity_tracker = services.popularity


def create_app() -> Flask:
    """Create and fully initialize one meteorological API application."""
    flask_application = Flask(__name__)

    # Flask-SQLAlchemy reads its connection settings during init_app(), so the
    # deployment configuration must be loaded before any extension is initialized.
    flask_application.config.from_envvar("APP_SETTINGS", silent=False)
    flask_application.config.setdefault(
        "SQLALCHEMY_DATABASE_URI",
        os.environ.get(
            "DATABASE_URL", "postgresql://user:password@postgres:5432/cnmost"
        ),
    )
    flask_application.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    db.init_app(flask_application)
    CORS(flask_application)
    api.init_app(flask_application)
    register_version_response_headers(flask_application)

    services = _create_runtime_services(flask_application)
    flask_application.extensions[RUNTIME_SERVICES_EXTENSION] = services
    _publish_legacy_globals(flask_application, services)
    return flask_application


# Preserve the established ``from app import application`` deployment contract.
application = create_app()
