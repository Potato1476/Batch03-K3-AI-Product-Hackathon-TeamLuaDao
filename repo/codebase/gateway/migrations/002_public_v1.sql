-- CHẮN public /v1 data model — CHAN-ARCHITECTURE.md §8.
--
-- The invariants are enforced here, not only in application code:
--   I2  no table has a column able to hold message content
--   I4  lookup prefixes never enter public access logs
--   I5  a guardian pair cannot exist without consent from the protected device
--   I6  every risk CHECK omits any reassuring label
--
-- Apply with:  psql "$CHAN_DATABASE_URL" < 002_public_v1.sql

BEGIN;

-- ---------------------------------------------------------------- analyses --
-- NO COLUMN MAY CONTAIN MESSAGE CONTENT (I2). Adding one is a design breach.
CREATE TABLE IF NOT EXISTS analyses (
  id                  text PRIMARY KEY,
  text_sha256         bytea NOT NULL,          -- hash of the normalised text
  risk                text NOT NULL CHECK (risk IN ('high','medium','unknown')),
  score               real NOT NULL CHECK (score >= 0 AND score <= 1),
  signals             jsonb NOT NULL DEFAULT '[]'::jsonb,  -- [{code,confidence}] — NEVER evidence
  source              text NOT NULL CHECK (source IN ('web','android','zalo_oa')),
  input_mode          text NOT NULL CHECK (input_mode IN ('manual','share','notification','sms_scan')),
  app_package         text,
  truncated           boolean NOT NULL DEFAULT false,
  blocklist_match     boolean NOT NULL DEFAULT false,
  engine_version      text NOT NULL,
  rule_version        text NOT NULL,
  device_id           text,
  created_at          timestamptz NOT NULL DEFAULT now()   -- TTL 90 days
);

-- Reject an evidence key inside the stored signals: the client receives
-- evidence, the database must never keep it. A CHECK cannot contain a
-- subquery, so the element scan lives in an IMMUTABLE helper.
CREATE OR REPLACE FUNCTION chan_signals_are_metadata_only(signals jsonb)
RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT AS $$
  SELECT jsonb_typeof(signals) = 'array' AND NOT EXISTS (
    SELECT 1
    FROM jsonb_array_elements(signals) AS signal
    WHERE signal ? 'evidence' OR signal ? 'text' OR signal ? 'explanation'
  );
$$;

ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_signals_have_no_evidence;
ALTER TABLE analyses ADD CONSTRAINT analyses_signals_have_no_evidence
  CHECK (chan_signals_are_metadata_only(signals));

CREATE INDEX IF NOT EXISTS analyses_created_idx ON analyses (created_at);
CREATE INDEX IF NOT EXISTS analyses_hash_idx ON analyses (text_sha256);

-- ----------------------------------------------------------------- devices --
-- Device token identity. §7.3: never a phone number, and it expires.
CREATE TABLE IF NOT EXISTS devices (
  id           text PRIMARY KEY,
  token_hash   bytea NOT NULL UNIQUE,
  platform     text NOT NULL CHECK (platform IN ('web','android','zalo_oa')),
  push_token   text,
  rotated_from text REFERENCES devices(id),
  expires_at   timestamptz NOT NULL,
  revoked_at   timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz
);
CREATE INDEX IF NOT EXISTS devices_expiry_idx ON devices (expires_at);

-- --------------------------------------------------------------- guardians --
-- Endpoints land in phase 3 (§13 roadmap), but the consent constraint exists
-- now: I5 must be enforced by the schema, not by whoever writes the endpoint.
CREATE TABLE IF NOT EXISTS guardian_pair_codes (
  code               char(6) PRIMARY KEY CHECK (code ~ '^[0-9]{6}$'),
  protected_device   text NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  expires_at         timestamptz NOT NULL,   -- 10 minutes (§4.6)
  consumed_at        timestamptz,
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS guardians (
  protected_device  text NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  guardian_device   text NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  consented_at      timestamptz NOT NULL,
  consent_source    text NOT NULL CHECK (consent_source = 'protected_device'),
  revoked_at        timestamptz,
  PRIMARY KEY (protected_device, guardian_device),
  CONSTRAINT guardians_no_self_pairing CHECK (protected_device <> guardian_device)
);

-- NO COLUMN MAY CONTAIN MESSAGE CONTENT (I5).
CREATE TABLE IF NOT EXISTS guardian_alerts (
  id                bigserial PRIMARY KEY,
  protected_device  text NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  guardian_device   text NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  risk              text NOT NULL CHECK (risk IN ('high','medium')),
  signals           text[] NOT NULL DEFAULT '{}',
  app_package       text,
  delivery          text NOT NULL DEFAULT 'pending'
                      CHECK (delivery IN ('pending','sent','failed','skipped')),
  sent_at           timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- feedback --
CREATE TABLE IF NOT EXISTS feedback (
  id           bigserial PRIMARY KEY,
  analysis_id  text NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  verdict      text NOT NULL CHECK (verdict IN ('correct','false_positive','false_negative')),
  contributed  boolean NOT NULL DEFAULT false,  -- forwarded to the training plane
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (analysis_id)
);

-- -------------------------------------------------------------- access_log --
-- Metadata only, 30-day life (§7.2). Note the absence of a prefix column:
-- logging lookup prefixes would erode I4 over time.
CREATE TABLE IF NOT EXISTS access_log (
  id          bigserial PRIMARY KEY,
  device_id   text,
  endpoint    text NOT NULL,
  status      integer NOT NULL,
  latency_ms  integer NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS access_log_created_idx ON access_log (created_at);

-- ------------------------------------------------------------- rate limits --
-- Fallback counter store used only when Redis is not configured.
CREATE TABLE IF NOT EXISTS rate_limit_counters (
  bucket      text PRIMARY KEY,
  hits        integer NOT NULL DEFAULT 0,
  expires_at  timestamptz NOT NULL
);

COMMIT;
