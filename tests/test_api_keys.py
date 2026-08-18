"""Security and lifecycle tests for the API-key domain service."""

from __future__ import annotations

import pytest
from flask import Flask

from core.ApiKeyModels import ApiKey, ApiKeyAuditEvent, ApiKeyRequest, ApiUsageEvent
from core.ApiKeyService import ApiKeyError, ApiKeyHasher, ApiKeyService, ApiKeyValidationError
from core.Models import db


@pytest.fixture
def api_key_service():
    """Provide an isolated relational store for credential lifecycle tests."""
    application = Flask("api-key-tests")
    application.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        ENV="test",
        API_KEY_DEFAULT_LIFETIME_DAYS=30,
    )
    db.init_app(application)
    context = application.app_context()
    context.push()
    db.create_all()
    try:
        yield ApiKeyService(application.config)
    finally:
        db.session.remove()
        db.drop_all()
        context.pop()


def test_hashes_are_salted_and_verify_without_storing_plaintext():
    """Ensure equal secrets receive independent memory-hard verifiers."""
    hasher = ApiKeyHasher()
    first = hasher.hash_secret("a-secure-test-secret")
    second = hasher.hash_secret("a-secure-test-secret")

    assert first.startswith("scrypt$")
    assert first != second
    assert "a-secure-test-secret" not in first
    assert hasher.verify("a-secure-test-secret", first)
    assert not hasher.verify("wrong-secret", first)


def test_request_issue_validate_rotate_and_revoke_lifecycle(api_key_service):
    """Exercise the complete credential lifecycle and irreversible transitions."""
    request = api_key_service.request_key(
        requester_name="Ada Lovelace",
        requester_email="ADA@example.test",
        organization="Analytical Weather Lab",
        purpose="Research access for forecast evaluation",
        scopes=["products:read", "forecast:read"],
    )

    assert request.status == "pending"
    assert request.requester_email == "ada@example.test"
    assert ApiKey.query.count() == 0

    issued = api_key_service.issue_request(
        request.id,
        actor="operator@example.test",
        approved_scopes=["products:read", "forecast:read"],
        lifetime_days=60,
    )

    persisted = db.session.get(ApiKey, issued.api_key.id)
    assert request.status == "issued"
    assert issued.plaintext.startswith("meteo_test_")
    assert issued.plaintext not in persisted.secret_hash
    assert "secretHash" not in persisted.to_dict()
    assert "secret_hash" not in persisted.to_dict()

    principal = api_key_service.validate(
        issued.plaintext, required_scopes=["forecast:read"], record_usage=True
    )
    assert principal.api_key_id == persisted.id
    assert principal.owner_email == "ada@example.test"
    assert principal.scopes == frozenset({"products:read", "forecast:read"})
    assert persisted.last_used_at is not None

    with pytest.raises(ApiKeyValidationError, match="required scope"):
        api_key_service.validate(issued.plaintext, required_scopes=["timeseries:read"])
    with pytest.raises(ApiKeyValidationError, match="invalid API key"):
        api_key_service.validate(issued.plaintext + "tampered")

    replacement = api_key_service.rotate(
        persisted.id, actor="operator@example.test", lifetime_days=90
    )
    assert replacement.plaintext != issued.plaintext
    assert replacement.api_key.rotated_from_id == persisted.id
    assert persisted.status == "rotated"
    with pytest.raises(ApiKeyValidationError, match="not active"):
        api_key_service.validate(issued.plaintext)
    assert (
        api_key_service.validate(replacement.plaintext).api_key_id
        == replacement.api_key.id
    )

    api_key_service.revoke(
        replacement.api_key.id,
        actor="operator@example.test",
        reason="research project completed",
    )
    with pytest.raises(ApiKeyValidationError, match="not active"):
        api_key_service.validate(replacement.plaintext)

    assert ApiKeyRequest.query.count() == 1
    assert ApiKey.query.count() == 2
    assert [
        event.action
        for event in ApiKeyAuditEvent.query.order_by(ApiKeyAuditEvent.occurred_at)
    ] == ["request.created", "key.issued", "key.rotated", "key.revoked"]


def test_request_rejects_unknown_scopes(api_key_service):
    """Ensure consumers cannot invent or self-grant authorization scopes."""
    with pytest.raises(ApiKeyError, match="unsupported scopes"):
        api_key_service.request_key(
            requester_name="Grace Hopper",
            requester_email="grace@example.test",
            organization=None,
            purpose="Evaluate a weather-data integration",
            scopes=["root:everything"],
        )


def test_issuance_cannot_escalate_beyond_requested_scopes(api_key_service):
    """Ensure review can reduce privileges but cannot add unrequested access."""
    request = api_key_service.request_key(
        requester_name="Katherine Johnson",
        requester_email="katherine@example.test",
        organization="Orbital Weather Group",
        purpose="Read product metadata for trajectory analysis",
        scopes=["products:read"],
    )

    with pytest.raises(ApiKeyError, match="subset"):
        api_key_service.issue_request(
            request.id,
            actor="operator@example.test",
            approved_scopes=["products:read", "forecast:read"],
        )

    assert request.status == "pending"
    assert ApiKey.query.count() == 0


def test_usage_events_are_consumer_attributed_and_reported(api_key_service):
    """Ensure request telemetry identifies consumers without storing secrets."""
    request = api_key_service.request_key(
        requester_name="Dorothy Vaughan",
        requester_email="dorothy@example.test",
        organization="Weather Computing Group",
        purpose="Evaluate forecast response performance",
        scopes=["forecast:read"],
    )
    issued = api_key_service.issue_request(request.id, actor="operator@example.test")
    principal = api_key_service.validate(issued.plaintext, ["forecast:read"])
    event = api_key_service.record_usage(
        principal, "GET", "/api/v1/products/<prod>/forecast/<place>", "1", 200, 12.5
    )
    report = api_key_service.usage_report(limit=10)

    assert ApiUsageEvent.query.count() == 1
    assert event.key_prefix == principal.key_prefix
    assert issued.plaintext not in str(event.to_dict())
    assert report["sampleSize"] == 1
    assert report["consumers"][0]["ownerEmail"] == "dorothy@example.test"
    assert report["routes"][0]["requests"] == 1
