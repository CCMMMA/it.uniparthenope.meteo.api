"""RESTX namespace for version 2 map metadata and Slurm resources."""

from flask_restx import Namespace, Resource
from flask import current_app, jsonify, request

from core.SlurmServices import SlurmServices
from core.DataStructuresV2 import maps, baseMaps, layers

api = Namespace('v2', description='Version 2 map metadata and Slurm endpoints.')


def _resolve_mapping_detail(data, name, field_name):
    """Resolve one entry from a static mapping and return a 404 payload when missing."""
    if name not in data:
        return jsonify({"errMsg": f"{field_name} not found.", "statusCode": 404}), 404
    return jsonify(data[name])


# FROM ORIGINAL : Internal Server Error
# TESTED - 1 problem
@api.route('/slurm/storage')
class SlurmStorage(Resource):
    """Resource handler for slurm storage operations."""
    @api.doc(summary="Get Slurm storage status", responses={200: "Storage status returned"})
    def get(self):
        """
        Return storage information collected from the Slurm environment.

        Example:
        `GET /v2/slurm/storage`
        """
        ss = SlurmServices(current_app.config)
        res = ss.get_storage_status()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/slurm/info')
class SlurmInfo(Resource):
    """Resource handler for slurm info operations."""
    @api.doc(summary="Get Slurm cluster information", responses={200: "Slurm information returned"})
    def get(self):
        """
        Return general cluster information from Slurm.

        Example:
        `GET /v2/slurm/info`
        """
        ss = SlurmServices(current_app.config)
        res = ss.sinfo()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/slurm/queue')
class SlurmQueue(Resource):
    """Resource handler for slurm info operations."""
    @api.doc(summary="Get Slurm queue information", responses={200: "Slurm queue returned"})
    def get(self):
        """
        Return the current Slurm queue snapshot.

        Example:
        `GET /v2/slurm/queue`
        """
        ss = SlurmServices(current_app.config)
        res = ss.squeue()
        return jsonify(res)


# TESTED AND WORKING
@api.route('/basemaps')
class BaseMaps(Resource):
    """Resource handler for base maps operations."""
    @api.doc(summary="List basemaps", responses={200: "Basemap catalog returned"})
    def get(self):
        """Handle GET requests for this resource."""
        return jsonify(baseMaps)


# TESTED AND WORKING
@api.route('/basemaps/<string:name>')
class BaseMapsByName(Resource):
    """Resource handler for base maps by name operations."""
    @api.doc(summary="Get a basemap by name", params={"name": "Basemap identifier"}, responses={200: "Basemap returned", 404: "Basemap not found"})
    def get(self, name):
        """Handle GET requests for this resource."""
        return _resolve_mapping_detail(baseMaps, name, "Basemap")


@api.route('/basemap/detail')
class BaseMapDetail(Resource):
    """Legacy compatibility alias for basemap detail lookups."""
    @api.doc(summary="Get a basemap by legacy detail route", params={"name": "Basemap identifier"}, responses={200: "Basemap returned", 404: "Basemap not found"})
    def get(self):
        """Handle GET requests for the legacy basemap detail alias."""
        name = request.args.get("name") or request.args.get("id")
        if not name:
            return jsonify({"errMsg": "Basemap not found.", "statusCode": 404}), 404
        return _resolve_mapping_detail(baseMaps, name, "Basemap")


# TESTED AND WORKING
@api.route('/layers')
class Layers(Resource):
    """Resource handler for layers operations."""
    @api.doc(summary="List layers", responses={200: "Layer catalog returned"})
    def get(self):
        """Handle GET requests for this resource."""
        return jsonify(layers)


# TESTED AND WORKING
# example : name = info
@api.route('/layers/<string:name>')
class LayersByName(Resource):
    """Resource handler for layers by name operations."""
    @api.doc(summary="Get a layer by name", params={"name": "Layer identifier"}, responses={200: "Layer returned", 404: "Layer not found"})
    def get(self, name):
        """Handle GET requests for this resource."""
        return _resolve_mapping_detail(layers, name, "Layer")


# TESTED AND WORKING
@api.route('/maps')
class Maps(Resource):
    """Resource handler for maps operations."""
    @api.doc(summary="List maps", responses={200: "Map catalog returned"})
    def get(self):
        """Handle GET requests for this resource."""
        return jsonify(maps)


# TESTED AND WORKING
# example : name = weather
@api.route('/maps/<string:name>')
class MapsByName(Resource):
    """Resource handler for maps by name operations."""
    @api.doc(summary="Get a map definition by name", params={"name": "Map identifier"}, responses={200: "Map definition returned", 404: "Map not found"})
    def get(self, name):
        """Handle GET requests for this resource."""
        return _resolve_mapping_detail(maps, name, "Map")
