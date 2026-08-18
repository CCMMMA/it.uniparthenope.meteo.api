"""Persistent domain models for API-key requests, credentials, and audit events."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from core.Models import db


def utcnow():
    """Return a timezone-independent UTC value suitable for current SQL columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ApiKeyRequest(db.Model):
    """Represent a consumer's request for an API credential."""

    __tablename__ = "api_key_requests"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    requester_name = db.Column(db.String(160), nullable=False)
    requester_email = db.Column(db.String(320), nullable=False, index=True)
    organization = db.Column(db.String(200), nullable=True)
    purpose = db.Column(db.Text, nullable=False)
    requested_scopes = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(24), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.String(160), nullable=True)
    review_note = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'issued', 'cancelled')",
            name="ck_api_key_requests_status",
        ),
    )

    def to_dict(self):
        """Return the requester-safe representation."""
        return {
            "id": self.id,
            "requesterName": self.requester_name,
            "requesterEmail": self.requester_email,
            "organization": self.organization,
            "purpose": self.purpose,
            "requestedScopes": list(self.requested_scopes or []),
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "reviewedAt": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class ApiKey(db.Model):
    """Store an API-key identity and verifier without storing its plaintext secret."""

    __tablename__ = "api_keys"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    request_id = db.Column(
        db.String(36), db.ForeignKey("api_key_requests.id"), nullable=True, index=True
    )
    key_prefix = db.Column(db.String(80), nullable=False, unique=True, index=True)
    secret_hash = db.Column(db.Text, nullable=False)
    label = db.Column(db.String(160), nullable=False)
    owner_email = db.Column(db.String(320), nullable=False, index=True)
    organization = db.Column(db.String(200), nullable=True)
    scopes = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(24), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    revoked_by = db.Column(db.String(160), nullable=True)
    revocation_reason = db.Column(db.Text, nullable=True)
    rotated_from_id = db.Column(
        db.String(36), db.ForeignKey("api_keys.id"), nullable=True, index=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('active', 'revoked', 'rotated', 'expired')",
            name="ck_api_keys_status",
        ),
    )

    def to_dict(self):
        """Return metadata that never exposes the secret verifier."""
        return {
            "id": self.id,
            "requestId": self.request_id,
            "keyPrefix": self.key_prefix,
            "label": self.label,
            "ownerEmail": self.owner_email,
            "organization": self.organization,
            "scopes": list(self.scopes or []),
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
            "lastUsedAt": self.last_used_at.isoformat() if self.last_used_at else None,
            "rotatedFromId": self.rotated_from_id,
        }


class ApiKeyAuditEvent(db.Model):
    """Record security-relevant API-key lifecycle transitions."""

    __tablename__ = "api_key_audit_events"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    api_key_id = db.Column(
        db.String(36), db.ForeignKey("api_keys.id"), nullable=True, index=True
    )
    request_id = db.Column(
        db.String(36), db.ForeignKey("api_key_requests.id"), nullable=True, index=True
    )
    action = db.Column(db.String(64), nullable=False, index=True)
    actor = db.Column(db.String(160), nullable=False)
    event_data = db.Column(db.JSON, nullable=False, default=dict)
    occurred_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    def to_dict(self):
        """Return an audit-safe representation."""
        return {
            "id": self.id,
            "apiKeyId": self.api_key_id,
            "requestId": self.request_id,
            "action": self.action,
            "actor": self.actor,
            "eventData": dict(self.event_data or {}),
            "occurredAt": self.occurred_at.isoformat() if self.occurred_at else None,
        }


class ApiUsageEvent(db.Model):
    """Record one authenticated API invocation without credential secrets."""

    __tablename__ = "api_usage_events"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    api_key_id = db.Column(
        db.String(36), db.ForeignKey("api_keys.id"), nullable=False, index=True
    )
    key_prefix = db.Column(db.String(80), nullable=False, index=True)
    owner_email = db.Column(db.String(320), nullable=False, index=True)
    organization = db.Column(db.String(200), nullable=True, index=True)
    method = db.Column(db.String(12), nullable=False)
    route = db.Column(db.String(255), nullable=False, index=True)
    api_version = db.Column(db.String(16), nullable=False, index=True)
    status_code = db.Column(db.Integer, nullable=False, index=True)
    duration_ms = db.Column(db.Float, nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    def to_dict(self):
        """Return an administrative representation with no secret material."""
        return {
            "id": self.id,
            "apiKeyId": self.api_key_id,
            "keyPrefix": self.key_prefix,
            "ownerEmail": self.owner_email,
            "organization": self.organization,
            "method": self.method,
            "route": self.route,
            "apiVersion": self.api_version,
            "statusCode": self.status_code,
            "durationMs": self.duration_ms,
            "occurredAt": self.occurred_at.isoformat() if self.occurred_at else None,
        }
