BEGIN;

ALTER TABLE recommendation.cf_recording DROP recording_mbid;
ALTER TABLE recommendation.cf_recording ADD COLUMN recording_mbid JSONB NOT NULL;

ALTER TABLE recommendation.cf_recording ADD CONSTRAINT user_id_unique UNIQUE (user_id);

COMMIT;
