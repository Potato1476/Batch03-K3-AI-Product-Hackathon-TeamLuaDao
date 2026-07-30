BEGIN;

-- Source metadata and conditional-request state contain no raw indicators.
CREATE TABLE IF NOT EXISTS intel_sources (
    name                       text PRIMARY KEY,
    enabled                    boolean NOT NULL DEFAULT false,
    rights_basis               text NOT NULL CHECK (
                                   rights_basis IN (
                                       'commercial_api_terms',
                                       'cc_by_4_0',
                                       'written_permission',
                                       'explicit_consent'
                                   )
                               ),
    update_interval_minutes    integer,
    etag                       text,
    last_modified              text,
    last_success_at            timestamptz,
    last_record_count          integer NOT NULL DEFAULT 0,
    last_error_code            text,
    updated_at                 timestamptz NOT NULL DEFAULT now()
);

INSERT INTO intel_sources (
    name, enabled, rights_basis, update_interval_minutes
) VALUES
    ('phishtank', true, 'commercial_api_terms', 60),
    ('openphish', false, 'written_permission', 720),
    ('phishvn', true, 'cc_by_4_0', NULL),
    ('user_report', true, 'explicit_consent', NULL)
ON CONFLICT (name) DO NOTHING;

CREATE TABLE IF NOT EXISTS intel_sync_runs (
    id               uuid PRIMARY KEY,
    source           text NOT NULL REFERENCES intel_sources(name),
    status           text NOT NULL CHECK (
                         status IN ('running', 'unchanged', 'succeeded', 'failed')
                     ),
    started_at       timestamptz NOT NULL DEFAULT now(),
    finished_at      timestamptz,
    record_count     integer,
    error_code       text
);

CREATE INDEX IF NOT EXISTS intel_sync_runs_source_idx
    ON intel_sync_runs (source, started_at DESC);

-- Raw URLs, phone numbers, and bank accounts are intentionally absent.
CREATE TABLE IF NOT EXISTS threat_indicators (
    kind               text NOT NULL CHECK (
                           kind IN ('account', 'phone', 'url')
                       ),
    hash                bytea NOT NULL,
    prefix              char(2) NOT NULL,
    origin              text NOT NULL REFERENCES intel_sources(name),
    source_item_hash    bytea NOT NULL,
    confidence          text NOT NULL CHECK (
                           confidence IN (
                               'feed_listed',
                               'community_reviewed',
                               'verified',
                               'partner_verified'
                           )
                       ),
    report_count        integer NOT NULL DEFAULT 1
                        CHECK (report_count > 0),
    first_seen          timestamptz NOT NULL,
    last_seen           timestamptz NOT NULL,
    active              boolean NOT NULL DEFAULT true,
    last_sync_run_id    uuid REFERENCES intel_sync_runs(id),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (kind, hash, origin),
    UNIQUE (origin, source_item_hash),
    CHECK (octet_length(hash) = 32),
    CHECK (octet_length(source_item_hash) = 32),
    CHECK (prefix = substring(encode(hash, 'hex') FROM 1 FOR 2))
);

CREATE INDEX IF NOT EXISTS threat_indicators_lookup_idx
    ON threat_indicators (kind, prefix)
    WHERE active;

CREATE INDEX IF NOT EXISTS threat_indicators_sync_idx
    ON threat_indicators (origin, last_sync_run_id);

-- The product backend submits hashes and evidence hashes only. No evidence
-- content, reporter identity, or raw indicator enters this database.
CREATE TABLE IF NOT EXISTS indicator_reports (
    id                    uuid PRIMARY KEY,
    kind                  text NOT NULL CHECK (
                              kind IN ('account', 'phone', 'url')
                          ),
    hash                  bytea NOT NULL,
    prefix                char(2) NOT NULL,
    reporter_hash         bytea NOT NULL,
    evidence_hash         bytea,
    consented             boolean NOT NULL CHECK (consented),
    status                text NOT NULL DEFAULT 'quarantined' CHECK (
                              status IN (
                                  'quarantined',
                                  'approved',
                                  'rejected',
                                  'expired'
                              )
                          ),
    submitted_by          text NOT NULL,
    submitted_at          timestamptz NOT NULL DEFAULT now(),
    reviewed_by           text,
    reviewed_at           timestamptz,
    review_reason         text,
    CHECK (octet_length(hash) = 32),
    CHECK (octet_length(reporter_hash) = 32),
    CHECK (evidence_hash IS NULL OR octet_length(evidence_hash) = 32),
    CHECK (prefix = substring(encode(hash, 'hex') FROM 1 FOR 2)),
    UNIQUE (kind, hash, reporter_hash)
);

CREATE INDEX IF NOT EXISTS indicator_reports_review_idx
    ON indicator_reports (submitted_at)
    WHERE status = 'quarantined';

CREATE INDEX IF NOT EXISTS indicator_reports_consensus_idx
    ON indicator_reports (kind, hash)
    WHERE status = 'approved';

CREATE TABLE IF NOT EXISTS indicator_report_audit (
    id              bigserial PRIMARY KEY,
    report_id       uuid NOT NULL REFERENCES indicator_reports(id),
    action          text NOT NULL CHECK (
                        action IN ('submitted', 'approved', 'rejected', 'expired')
                    ),
    actor           text NOT NULL,
    reason_code     text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

COMMIT;
