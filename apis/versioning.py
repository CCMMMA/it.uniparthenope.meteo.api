"""Shared metadata and response handling for governed API versions."""

from __future__ import annotations

from flask import Flask, request


CURRENT_API_VERSION = "1"
CURRENT_API_BASE_PATH = f"/api/v{CURRENT_API_VERSION}"
IMPLEMENTATION_VERSION = "4.01"

def _legacy_successor(path):
    """Return a successor URI only for legacy families with functional v1 parity."""
    parts = path.strip("/").split("/")
    if len(parts) == 4 and parts[0] == "products" and parts[2] == "forecast":
        return f"/api/v1/products/{parts[1]}/forecast/{parts[3]}"
    if len(parts) in (4, 5) and parts[0] == "products" and parts[2] == "timeseries":
        if len(parts) == 5 and parts[4] != "csv":
            return None
        suffix = "/csv" if len(parts) == 5 else ""
        return f"/api/v1/products/{parts[1]}/timeseries/{parts[3]}{suffix}"
    return None


def register_version_response_headers(application: Flask) -> None:
    """Identify responses produced by a governed, versioned API contract."""

    @application.after_request
    def add_version_response_headers(response):
        if request.path == CURRENT_API_BASE_PATH or request.path.startswith(
            f"{CURRENT_API_BASE_PATH}/"
        ):
            response.headers["API-Version"] = CURRENT_API_VERSION
        else:
            successor = _legacy_successor(request.path)
            if successor is not None:
                response.headers["Deprecation"] = "true"
                response.headers.add("Link", f'<{successor}>; rel="successor-version"')
                sunset = application.config.get("LEGACY_API_SUNSET")
                if sunset:
                    response.headers["Sunset"] = str(sunset)
        return response
