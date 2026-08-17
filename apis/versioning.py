"""Shared metadata and response handling for governed API versions."""

from __future__ import annotations

from flask import Flask, request


CURRENT_API_VERSION = "1"
CURRENT_API_BASE_PATH = f"/api/v{CURRENT_API_VERSION}"
IMPLEMENTATION_VERSION = "4.01"


def register_version_response_headers(application: Flask) -> None:
    """Identify responses produced by a governed, versioned API contract."""

    @application.after_request
    def add_version_response_headers(response):
        if request.path == CURRENT_API_BASE_PATH or request.path.startswith(
            f"{CURRENT_API_BASE_PATH}/"
        ):
            response.headers["API-Version"] = CURRENT_API_VERSION
        return response
