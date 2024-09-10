from flask_restx import Api

from .namespace_login import api as ns_login
from .namespace_apps import api as ns_apps
from .namespace_box import api as ns_box
from .namespace_legal import api as ns_legal
from .namespace_places import api as ns_places
from .namespace_products import api as ns_products
from .namespace_v2 import api as ns_v2
from .namespace_version import api as ns_version
from .namespace_webcam import api as ns_webcam

api = Api()

# aggregation of namespace
api.add_namespace(ns_login)
api.add_namespace(ns_apps)
api.add_namespace(ns_box)
api.add_namespace(ns_legal)
api.add_namespace(ns_places)
api.add_namespace(ns_products)
api.add_namespace(ns_v2)
api.add_namespace(ns_version)
api.add_namespace(ns_webcam)


