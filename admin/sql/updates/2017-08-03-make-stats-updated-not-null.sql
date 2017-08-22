BEGIN;

UPDATE statistics.user SET last_updated = to_timestamp(0) WHERE last_updated IS NULL;
UPDATE statistics.artist SET last_updated = to_timestamp(0) WHERE last_updated IS NULL;
UPDATE statistics.release SET last_updated = to_timestamp(0) WHERE last_updated IS NULL;
UPDATE statistics.recording SET last_updated = to_timestamp(0) WHERE last_updated IS NULL;

ALTER TABLE statistics.user ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.user ALTER COLUMN last_updated SET DEFAULT NOW();

ALTER TABLE statistics.artist ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.artist ALTER COLUMN last_updated SET DEFAULT NOW();


ALTER TABLE statistics.release ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.release ALTER COLUMN last_updated SET DEFAULT NOW();

ALTER TABLE statistics.recording ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.recording ALTER COLUMN last_updated SET DEFAULT NOW();

COMMIT;
