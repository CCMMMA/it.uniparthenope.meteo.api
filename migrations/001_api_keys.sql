BEGIN;

CREATE TABLE api_key_requests (
    id VARCHAR(36) PRIMARY KEY,
    requester_name VARCHAR(160) NOT NULL,
    requester_email VARCHAR(320) NOT NULL,
    organization VARCHAR(200),
    purpose TEXT NOT NULL,
    requested_scopes JSON NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'issued', 'cancelled')),
    created_at TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP,
    reviewed_by VARCHAR(160),
    review_note TEXT
);
CREATE INDEX ix_api_key_requests_requester_email ON api_key_requests (requester_email);
CREATE INDEX ix_api_key_requests_status ON api_key_requests (status);

CREATE TABLE api_keys (
    id VARCHAR(36) PRIMARY KEY,
    request_id VARCHAR(36) REFERENCES api_key_requests(id),
    key_prefix VARCHAR(80) NOT NULL UNIQUE,
    secret_hash TEXT NOT NULL,
    label VARCHAR(160) NOT NULL,
    owner_email VARCHAR(320) NOT NULL,
    organization VARCHAR(200),
    scopes JSON NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'revoked', 'rotated', 'expired')),
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by VARCHAR(160),
    revocation_reason TEXT,
    rotated_from_id VARCHAR(36) REFERENCES api_keys(id)
);
CREATE INDEX ix_api_keys_request_id ON api_keys (request_id);
CREATE INDEX ix_api_keys_key_prefix ON api_keys (key_prefix);
CREATE INDEX ix_api_keys_owner_email ON api_keys (owner_email);
CREATE INDEX ix_api_keys_status ON api_keys (status);
CREATE INDEX ix_api_keys_expires_at ON api_keys (expires_at);
CREATE INDEX ix_api_keys_rotated_from_id ON api_keys (rotated_from_id);

CREATE TABLE api_key_audit_events (
    id VARCHAR(36) PRIMARY KEY,
    api_key_id VARCHAR(36) REFERENCES api_keys(id),
    request_id VARCHAR(36) REFERENCES api_key_requests(id),
    action VARCHAR(64) NOT NULL,
    actor VARCHAR(160) NOT NULL,
    event_data JSON NOT NULL,
    occurred_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_api_key_audit_events_api_key_id ON api_key_audit_events (api_key_id);
CREATE INDEX ix_api_key_audit_events_request_id ON api_key_audit_events (request_id);
CREATE INDEX ix_api_key_audit_events_action ON api_key_audit_events (action);
CREATE INDEX ix_api_key_audit_events_occurred_at ON api_key_audit_events (occurred_at);

COMMIT;
