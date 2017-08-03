BEGIN;

-- XXX(param): What should values that are null already be set to here now?
-- timestamp 0 or NOW() ?

ALTER TABLE statistics.user ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.user ALTER COLUMN last_updated SET DEFAULT NOW();

ALTER TABLE statistics.artist ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.artist ALTER COLUMN last_updated SET DEFAULT NOW();


ALTER TABLE statistics.release ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.release ALTER COLUMN last_updated SET DEFAULT NOW();

ALTER TABLE statistics.recording ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.recording ALTER COLUMN last_updated SET DEFAULT NOW();

COMMIT;
