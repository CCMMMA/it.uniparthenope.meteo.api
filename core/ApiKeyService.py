"""Secure API-key request, issuance, validation, rotation, and revocation services."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, Optional, Set

from core.ApiKeyModels import ApiKey, ApiKeyAuditEvent, ApiKeyRequest, utcnow
from core.Models import db


DEFAULT_ALLOWED_SCOPES = frozenset(
    {
        "products:read",
        "places:read",
        "forecast:read",
        "timeseries:read",
        "imagery:read",
        "operations:cache",
        "keys:admin",
    }
)


class ApiKeyError(ValueError):
    """Base class for API-key domain failures."""


class ApiKeyNotFound(ApiKeyError):
    """Raised when a request or credential cannot be resolved."""


class ApiKeyStateError(ApiKeyError):
    """Raised when an operation violates the credential lifecycle."""


class ApiKeyValidationError(ApiKeyError):
    """Raised when a presented credential is invalid or unauthorized."""


@dataclass(frozen=True)
class IssuedApiKey:
    """Carry a one-time plaintext credential beside its persistent metadata."""

    api_key: ApiKey
    plaintext: str


@dataclass(frozen=True)
class ApiKeyPrincipal:
    """Represent the authenticated consumer identity returned by validation."""

    api_key_id: str
    key_prefix: str
    owner_email: str
    organization: Optional[str]
    scopes: frozenset


class ApiKeyHasher:
    """Hash and verify secrets using salted, memory-hard scrypt."""

    algorithm = "scrypt"

    def __init__(self, n=16384, r=8, p=1, salt_bytes=16, key_bytes=32):
        if n < 16384 or n & (n - 1):
            raise ValueError("scrypt n must be a power of two and at least 16384")
        self.n = int(n)
        self.r = int(r)
        self.p = int(p)
        self.salt_bytes = int(salt_bytes)
        self.key_bytes = int(key_bytes)

    @staticmethod
    def _encode(value):
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    @staticmethod
    def _decode(value):
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def hash_secret(self, secret):
        """Return a self-describing salted verifier for one secret."""
        salt = secrets.token_bytes(self.salt_bytes)
        derived = hashlib.scrypt(
            secret.encode("utf-8"),
            salt=salt,
            n=self.n,
            r=self.r,
            p=self.p,
            dklen=self.key_bytes,
        )
        return "$".join(
            (
                self.algorithm,
                str(self.n),
                str(self.r),
                str(self.p),
                self._encode(salt),
                self._encode(derived),
            )
        )

    def verify(self, secret, encoded_hash):
        """Verify a secret in constant time using parameters stored with its hash."""
        try:
            algorithm, n, r, p, salt_value, expected_value = encoded_hash.split("$")
            if algorithm != self.algorithm:
                return False
            n_value, r_value, p_value = int(n), int(r), int(p)
            if n_value > self.n or r_value > self.r or p_value > self.p:
                return False
            salt = self._decode(salt_value)
            expected = self._decode(expected_value)
            if len(salt) != self.salt_bytes or len(expected) != self.key_bytes:
                return False
            actual = hashlib.scrypt(
                secret.encode("utf-8"),
                salt=salt,
                n=n_value,
                r=r_value,
                p=p_value,
                dklen=len(expected),
            )
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(actual, expected)


class ApiKeyService:
    """Coordinate credential lifecycle operations and their audit records."""

    def __init__(self, config, session=None, hasher=None):
        self.session = session if session is not None else db.session
        environment = str(
            config.get("API_KEY_ENVIRONMENT", config.get("ENV", "dev"))
        )
        self.environment = (
            re.sub(r"[^a-z0-9-]", "-", environment.lower()).strip("-") or "dev"
        )
        self.default_lifetime_days = int(config.get("API_KEY_DEFAULT_LIFETIME_DAYS", 365))
        configured_scopes = config.get("API_KEY_ALLOWED_SCOPES", DEFAULT_ALLOWED_SCOPES)
        if isinstance(configured_scopes, str):
            configured_scopes = configured_scopes.split(",")
        self.allowed_scopes = frozenset(
            str(scope).strip() for scope in configured_scopes if str(scope).strip()
        )
        self.hasher = hasher or ApiKeyHasher(
            n=int(config.get("API_KEY_SCRYPT_N", 16384)),
            r=int(config.get("API_KEY_SCRYPT_R", 8)),
            p=int(config.get("API_KEY_SCRYPT_P", 1)),
        )

    def _normalize_scopes(self, scopes: Iterable[str]) -> list:
        normalized = sorted({str(scope).strip() for scope in scopes if str(scope).strip()})
        if not normalized:
            raise ApiKeyError("at least one scope is required")
        unknown = set(normalized) - self.allowed_scopes
        if unknown:
            raise ApiKeyError("unsupported scopes: " + ", ".join(sorted(unknown)))
        return normalized

    def _audit(self, action, actor, api_key=None, request=None, event_data=None):
        self.session.add(
            ApiKeyAuditEvent(
                api_key_id=api_key.id if api_key else None,
                request_id=request.id if request else None,
                action=action,
                actor=actor,
                event_data=event_data or {},
            )
        )

    def request_key(
        self, requester_name, requester_email, organization, purpose, scopes
    ):
        """Create a pending request without generating credential material."""
        if not str(requester_name).strip() or "@" not in str(requester_email):
            raise ApiKeyError("requester name and a valid email are required")
        if len(str(purpose).strip()) < 10:
            raise ApiKeyError("purpose must contain at least 10 characters")
        request = ApiKeyRequest(
            requester_name=str(requester_name).strip(),
            requester_email=str(requester_email).strip().lower(),
            organization=str(organization).strip() if organization else None,
            purpose=str(purpose).strip(),
            requested_scopes=self._normalize_scopes(scopes),
            status="pending",
        )
        self.session.add(request)
        self.session.flush()
        self._audit("request.created", request.requester_email, request=request)
        self.session.commit()
        return request

    def issue_request(
        self, request_id, actor, approved_scopes=None, lifetime_days=None, label=None
    ):
        """Approve a pending request and return its plaintext credential exactly once."""
        request = self.session.get(ApiKeyRequest, request_id)
        if request is None:
            raise ApiKeyNotFound("API-key request not found")
        if request.status not in {"pending", "approved"}:
            raise ApiKeyStateError("only pending or approved requests can be issued")
        scopes = self._normalize_scopes(
            request.requested_scopes if approved_scopes is None else approved_scopes
        )
        if not set(scopes).issubset(set(request.requested_scopes or [])):
            raise ApiKeyError("approved scopes must be a subset of requested scopes")
        credential = self._new_key(
            owner_email=request.requester_email,
            organization=request.organization,
            scopes=scopes,
            label=label or request.organization or request.requester_name,
            lifetime_days=lifetime_days,
            request_id=request.id,
        )
        request.status = "issued"
        request.reviewed_at = utcnow()
        request.reviewed_by = actor
        self._audit(
            "key.issued",
            actor,
            api_key=credential.api_key,
            request=request,
            event_data={"scopes": scopes},
        )
        self.session.commit()
        return credential

    def _new_key(
        self,
        owner_email,
        organization,
        scopes,
        label,
        lifetime_days=None,
        request_id=None,
        rotated_from_id=None,
    ):
        public_id = secrets.token_urlsafe(9).rstrip("=")
        key_prefix = "meteo_{}_{}".format(self.environment, public_id)
        secret = secrets.token_urlsafe(32)
        plaintext = "{}.{}".format(key_prefix, secret)
        days = self.default_lifetime_days if lifetime_days is None else int(lifetime_days)
        if days <= 0:
            raise ApiKeyError("credential lifetime must be positive")
        api_key = ApiKey(
            request_id=request_id,
            key_prefix=key_prefix,
            secret_hash=self.hasher.hash_secret(secret),
            label=str(label).strip(),
            owner_email=str(owner_email).strip().lower(),
            organization=organization,
            scopes=self._normalize_scopes(scopes),
            status="active",
            expires_at=utcnow() + timedelta(days=days),
            rotated_from_id=rotated_from_id,
        )
        self.session.add(api_key)
        self.session.flush()
        return IssuedApiKey(api_key=api_key, plaintext=plaintext)

    @staticmethod
    def _split_plaintext(plaintext):
        if len(str(plaintext)) > 512:
            raise ApiKeyValidationError("invalid API-key format")
        try:
            prefix, secret = str(plaintext).split(".", 1)
        except ValueError as error:
            raise ApiKeyValidationError("invalid API-key format") from error
        if not prefix.startswith("meteo_") or len(secret) < 32:
            raise ApiKeyValidationError("invalid API-key format")
        return prefix, secret

    def validate(self, plaintext, required_scopes=(), record_usage=False):
        """Validate a credential and return its consumer principal."""
        prefix, secret = self._split_plaintext(plaintext)
        api_key = self.session.query(ApiKey).filter_by(key_prefix=prefix).one_or_none()
        if api_key is None or not self.hasher.verify(secret, api_key.secret_hash):
            raise ApiKeyValidationError("invalid API key")
        if api_key.status != "active":
            raise ApiKeyValidationError("API key is not active")
        now = utcnow()
        if api_key.expires_at is not None and api_key.expires_at <= now:
            api_key.status = "expired"
            self.session.commit()
            raise ApiKeyValidationError("API key has expired")
        required = set(required_scopes)
        granted: Set[str] = set(api_key.scopes or [])
        if "*" not in granted and not required.issubset(granted):
            raise ApiKeyValidationError("API key lacks required scope")
        if record_usage:
            api_key.last_used_at = now
            self.session.commit()
        return ApiKeyPrincipal(
            api_key_id=api_key.id,
            key_prefix=api_key.key_prefix,
            owner_email=api_key.owner_email,
            organization=api_key.organization,
            scopes=frozenset(granted),
        )

    def revoke(self, api_key_id, actor, reason):
        """Revoke an active credential without deleting its audit identity."""
        api_key = self.session.get(ApiKey, api_key_id)
        if api_key is None:
            raise ApiKeyNotFound("API key not found")
        if api_key.status != "active":
            raise ApiKeyStateError("only active API keys can be revoked")
        api_key.status = "revoked"
        api_key.revoked_at = utcnow()
        api_key.revoked_by = actor
        api_key.revocation_reason = str(reason).strip()
        self._audit(
            "key.revoked",
            actor,
            api_key=api_key,
            event_data={"reason": api_key.revocation_reason},
        )
        self.session.commit()
        return api_key

    def rotate(self, api_key_id, actor, lifetime_days=None):
        """Replace an active credential and return the new plaintext exactly once."""
        api_key = self.session.get(ApiKey, api_key_id)
        if api_key is None:
            raise ApiKeyNotFound("API key not found")
        if api_key.status != "active":
            raise ApiKeyStateError("only active API keys can be rotated")
        replacement = self._new_key(
            owner_email=api_key.owner_email,
            organization=api_key.organization,
            scopes=api_key.scopes,
            label=api_key.label,
            lifetime_days=lifetime_days,
            request_id=api_key.request_id,
            rotated_from_id=api_key.id,
        )
        api_key.status = "rotated"
        api_key.revoked_at = utcnow()
        api_key.revoked_by = actor
        api_key.revocation_reason = "rotated"
        self._audit(
            "key.rotated",
            actor,
            api_key=replacement.api_key,
            event_data={"rotatedFromId": api_key.id},
        )
        self.session.commit()
        return replacement
