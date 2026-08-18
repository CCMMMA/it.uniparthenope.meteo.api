BEGIN;

CREATE TABLE api_usage_events (
    id VARCHAR(36) PRIMARY KEY,
    api_key_id VARCHAR(36) NOT NULL REFERENCES api_keys(id),
    key_prefix VARCHAR(80) NOT NULL,
    owner_email VARCHAR(320) NOT NULL,
    organization VARCHAR(200),
    method VARCHAR(12) NOT NULL,
    route VARCHAR(255) NOT NULL,
    api_version VARCHAR(16) NOT NULL,
    status_code INTEGER NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL,
    occurred_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_api_usage_events_api_key_id ON api_usage_events (api_key_id);
CREATE INDEX ix_api_usage_events_key_prefix ON api_usage_events (key_prefix);
CREATE INDEX ix_api_usage_events_owner_email ON api_usage_events (owner_email);
CREATE INDEX ix_api_usage_events_organization ON api_usage_events (organization);
CREATE INDEX ix_api_usage_events_route ON api_usage_events (route);
CREATE INDEX ix_api_usage_events_api_version ON api_usage_events (api_version);
CREATE INDEX ix_api_usage_events_status_code ON api_usage_events (status_code);
CREATE INDEX ix_api_usage_events_occurred_at ON api_usage_events (occurred_at);

COMMIT;
