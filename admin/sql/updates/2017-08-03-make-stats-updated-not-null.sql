BEGIN;

ALTER TABLE statistics.user ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.user ALTER COLUMN last_updated SET DEFAULT NOW();

ALTER TABLE statistics.artist ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.artist ALTER COLUMN last_updated SET DEFAULT NOW();


ALTER TABLE statistics.release ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.release ALTER COLUMN last_updated SET DEFAULT NOW();

ALTER TABLE statistics.recording ALTER COLUMN last_updated SET NOT NULL;
ALTER TABLE statistics.recording ALTER COLUMN last_updated SET DEFAULT NOW();

COMMIT;
