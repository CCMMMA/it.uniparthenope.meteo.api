"""Flask-RESTX API configuration and namespace registration."""

from flask_restx import Api

from .namespace_apps import api as ns_apps
from .namespace_box import api as ns_box
from .namespace_legal import api as ns_legal
from .namespace_places import api as ns_places
from .namespace_products import api as ns_products
from .namespace_v2 import api as ns_v2
from .namespace_version import api as ns_version
from .namespace_webcam import api as ns_webcam
from .namespace_instruments import api as ns_instruments
from .namespace_api_v1 import api as ns_api_v1
from .namespace_api_v1_products import api as ns_api_v1_products
from .namespace_api_v1_admin import api as ns_api_v1_admin
from .versioning import CURRENT_API_BASE_PATH

api = Api(
    title="University of Naples Parthenope Meteo API",
    version="4.01",
    description=(
        "Formal API surface for forecast products, places, legal content, application integrations, "
        "map metadata, and operational resources used by the Parthenope meteorological platform."
    ),
    doc="/",
    authorizations={
        "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    },
)

# aggregation of namespace
api.add_namespace(ns_apps)
api.add_namespace(ns_box)
api.add_namespace(ns_legal)
api.add_namespace(ns_places)
api.add_namespace(ns_products)
api.add_namespace(ns_v2)
api.add_namespace(ns_version)
api.add_namespace(ns_webcam)
api.add_namespace(ns_instruments)
api.add_namespace(ns_api_v1, path=CURRENT_API_BASE_PATH)
api.add_namespace(ns_api_v1_products, path=f"{CURRENT_API_BASE_PATH}/products")
api.add_namespace(ns_api_v1_admin, path=f"{CURRENT_API_BASE_PATH}/admin")
