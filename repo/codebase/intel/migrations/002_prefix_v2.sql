BEGIN;

-- Upgrade databases created with the former two-hex lookup contract.
DO $$
DECLARE
    item record;
BEGIN
    FOR item IN
        SELECT conrelid::regclass AS table_name, conname
        FROM pg_constraint
        WHERE contype = 'c'
          AND conrelid IN (
              'threat_indicators'::regclass,
              'indicator_reports'::regclass
          )
          AND pg_get_constraintdef(oid) LIKE '%encode(hash, ''hex'')%FOR 2%'
    LOOP
        EXECUTE format(
            'ALTER TABLE %s DROP CONSTRAINT %I',
            item.table_name,
            item.conname
        );
    END LOOP;
END $$;

ALTER TABLE threat_indicators
    ALTER COLUMN prefix TYPE char(5);
UPDATE threat_indicators
SET prefix = substring(encode(hash, 'hex') FROM 1 FOR 5);
ALTER TABLE threat_indicators
    DROP CONSTRAINT IF EXISTS threat_indicators_prefix_v2_check;
ALTER TABLE threat_indicators
    ADD CONSTRAINT threat_indicators_prefix_v2_check
    CHECK (prefix = substring(encode(hash, 'hex') FROM 1 FOR 5));

ALTER TABLE indicator_reports
    ALTER COLUMN prefix TYPE char(5);
UPDATE indicator_reports
SET prefix = substring(encode(hash, 'hex') FROM 1 FOR 5);
ALTER TABLE indicator_reports
    DROP CONSTRAINT IF EXISTS indicator_reports_prefix_v2_check;
ALTER TABLE indicator_reports
    ADD CONSTRAINT indicator_reports_prefix_v2_check
    CHECK (prefix = substring(encode(hash, 'hex') FROM 1 FOR 5));

COMMIT;
