BEGIN;

CREATE TABLE IF NOT EXISTS training_scenarios (
    id                    uuid PRIMARY KEY,
    redacted_text         text,
    text_sha256           bytea NOT NULL UNIQUE,
    signals               text[] NOT NULL DEFAULT '{}',
    risk                  text NOT NULL
                          CHECK (risk IN ('high', 'medium', 'unknown')),
    is_phishing           boolean NOT NULL,
    origin                text NOT NULL,
    source_ref_hash       bytea,
    rights_basis          text NOT NULL CHECK (
                              rights_basis IN (
                                  'explicit_consent',
                                  'licensed_threat_intel',
                                  'synthetic'
                              )
                          ),
    consented             boolean NOT NULL DEFAULT false,
    redaction_confirmed   boolean NOT NULL CHECK (redaction_confirmed),
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
    CHECK (
        signals <@ ARRAY[
            'mao_danh_tham_quyen',
            'yeu_cau_bi_mat',
            'ap_luc_thoi_gian',
            'tk_ca_nhan',
            'cai_app_ngoai',
            'loi_ich_bat_thuong',
            'chuyen_kenh',
            'yeu_cau_otp'
        ]::text[]
    ),
    CHECK (
        (rights_basis = 'explicit_consent' AND consented)
        OR (rights_basis <> 'explicit_consent' AND NOT consented)
    ),
    CHECK (
        (status IN ('quarantined', 'approved') AND redacted_text IS NOT NULL)
        OR (status IN ('rejected', 'expired') AND redacted_text IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS training_scenarios_approved_idx
    ON training_scenarios (submitted_at)
    WHERE status = 'approved';

CREATE INDEX IF NOT EXISTS training_scenarios_quarantine_idx
    ON training_scenarios (submitted_at)
    WHERE status = 'quarantined';

CREATE TABLE IF NOT EXISTS training_scenario_audit (
    id              bigserial PRIMARY KEY,
    scenario_id     uuid NOT NULL REFERENCES training_scenarios(id),
    action          text NOT NULL CHECK (
                        action IN (
                            'submitted',
                            'approved',
                            'rejected',
                            'expired'
                        )
                    ),
    actor           text NOT NULL,
    reason_code     text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- This table contains metadata and aggregate metrics only, never message text.
CREATE TABLE IF NOT EXISTS training_runs (
    id                         uuid PRIMARY KEY,
    idempotency_key            text NOT NULL UNIQUE,
    status                     text NOT NULL DEFAULT 'queued' CHECK (
                                   status IN (
                                       'queued',
                                       'running',
                                       'promoted',
                                       'rejected',
                                       'failed'
                                   )
                               ),
    submitted_by               text NOT NULL,
    submitted_at               timestamptz NOT NULL DEFAULT now(),
    started_at                 timestamptz,
    finished_at                timestamptz,
    approved_scenario_count    integer,
    candidate_version          text,
    metrics                    jsonb,
    promotion_reasons          text[] NOT NULL DEFAULT '{}',
    error_code                 text
);

CREATE INDEX IF NOT EXISTS training_runs_queue_idx
    ON training_runs (submitted_at)
    WHERE status = 'queued';

-- Artifact URIs point to a private object-store bucket or persistent mount.
CREATE TABLE IF NOT EXISTS model_versions (
    version             text PRIMARY KEY,
    artifact_uri        text NOT NULL,
    artifact_sha256     char(64) NOT NULL,
    metrics             jsonb NOT NULL,
    status              text NOT NULL CHECK (
                            status IN ('active', 'archived', 'rejected')
                        ),
    training_run_id     uuid NOT NULL REFERENCES training_runs(id),
    created_at          timestamptz NOT NULL DEFAULT now(),
    promoted_at         timestamptz
);

CREATE UNIQUE INDEX IF NOT EXISTS model_versions_one_active_idx
    ON model_versions ((status))
    WHERE status = 'active';

COMMIT;
