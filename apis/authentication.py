"""Observation-only API-key authentication for transitional legacy routes."""

from __future__ import annotations

from functools import wraps
from time import perf_counter

from flask import Flask, current_app, g, jsonify, request

from core.ApiKeyService import ApiKeyValidationError
from core.Logger import logger
from core.RuntimeServices import RUNTIME_SERVICES_EXTENSION


OBSERVATION_HEADER = "API-Key-Observation"
API_KEY_HEADER = "X-API-Key"


def require_api_key(*required_scopes):
    """Enforce a scoped consumer key for one governed v1 handler."""
    def decorate(handler):
        @wraps(handler)
        def authenticated(*args, **kwargs):
            plaintext = request.headers.get(API_KEY_HEADER)
            if not plaintext:
                response = jsonify(error={"code": "api_key_required", "message": "X-API-Key is required"})
                response.status_code = 401
                return response
            try:
                principal = current_app.extensions[RUNTIME_SERVICES_EXTENSION].api_keys.validate(
                    plaintext, required_scopes=required_scopes, record_usage=False
                )
            except ApiKeyValidationError as error:
                status = 403 if "scope" in str(error).lower() else 401
                code = "insufficient_scope" if status == 403 else "invalid_api_key"
                response = jsonify(error={"code": code, "message": str(error)})
                response.status_code = status
                return response
            g.api_key_principal = principal
            g.api_key_required_scopes = required_scopes
            return handler(*args, **kwargs)
        return authenticated
    return decorate


def legacy_required_scopes(path):
    """Return the future scope classification for one legacy request path."""
    if path.startswith("/products/"):
        if "/invalidate/" in path or "/rebuild/" in path:
            return ("operations:cache",)
        if "/timeseries/" in path:
            return ("timeseries:read",)
        if any(
            token in path
            for token in ("/plot", "/legend/", "/map/image", "/resource/forecast/")
        ):
            return ("imagery:read",)
        if "/forecast/" in path or "/grib/" in path:
            return ("forecast:read",)
        return ("products:read",)
    if path == "/products":
        return ("products:read",)
    if path.startswith("/places"):
        return ("places:read",)
    if path.startswith("/apps/owm/"):
        return ("imagery:read",)
    return ()


def _safe_prefix(plaintext):
    """Return only the non-secret lookup component for diagnostics."""
    return str(plaintext).split(".", 1)[0][:80]


def register_api_key_observation(application: Flask) -> None:
    """Observe optional legacy credentials without enforcing authentication."""

    @application.before_request
    def observe_legacy_api_key():
        g.request_started_at = perf_counter()
        g.api_key_observation = "not-applicable"
        g.api_key_principal = None
        g.api_key_required_scopes = ()

        if request.path == "/api/v1" or request.path.startswith("/api/v1/"):
            return None

        plaintext = request.headers.get(API_KEY_HEADER)
        if not plaintext:
            g.api_key_observation = "absent"
            return None

        required_scopes = legacy_required_scopes(request.path)
        g.api_key_required_scopes = required_scopes
        prefix = _safe_prefix(plaintext)
        try:
            service = current_app.extensions[RUNTIME_SERVICES_EXTENSION].api_keys
            principal = service.validate(
                plaintext,
                required_scopes=required_scopes,
                record_usage=False,
            )
        except ApiKeyValidationError as validation_error:
            g.api_key_observation = "invalid"
            logger.info(
                "Legacy API-key observation invalid: path=%s prefix=%s scopes=%s reason=%s",
                request.path,
                prefix,
                ",".join(required_scopes),
                validation_error,
            )
        except Exception as service_error:
            # Observation must never become accidental enforcement when the
            # credential database is unavailable or not yet migrated.
            g.api_key_observation = "unavailable"
            logger.error(
                "Legacy API-key observation unavailable: path=%s prefix=%s error_type=%s",
                request.path,
                prefix,
                type(service_error).__name__,
            )
        else:
            g.api_key_observation = "valid"
            g.api_key_principal = principal
            logger.info(
                "Legacy API-key observation valid: path=%s prefix=%s scopes=%s",
                request.path,
                principal.key_prefix,
                ",".join(required_scopes),
            )
        return None

    @application.after_request
    def publish_api_key_observation(response):
        if request.headers.get(API_KEY_HEADER) and not (
            request.path == "/api/v1" or request.path.startswith("/api/v1/")
        ):
            response.headers[OBSERVATION_HEADER] = getattr(
                g, "api_key_observation", "unavailable"
            )
        principal = getattr(g, "api_key_principal", None)
        if principal is not None:
            route = request.url_rule.rule if request.url_rule is not None else request.path
            api_version = "1" if request.path.startswith("/api/v1/") else "legacy"
            try:
                current_app.extensions[RUNTIME_SERVICES_EXTENSION].api_keys.record_usage(
                    principal=principal,
                    method=request.method,
                    route=route,
                    api_version=api_version,
                    status_code=response.status_code,
                    duration_ms=(perf_counter() - getattr(g, "request_started_at", perf_counter())) * 1000.0,
                )
            except Exception as usage_error:
                try:
                    current_app.extensions[RUNTIME_SERVICES_EXTENSION].api_keys.session.rollback()
                except Exception:
                    pass
                logger.error("API usage event unavailable: route=%s error_type=%s", route, type(usage_error).__name__)
        return response
