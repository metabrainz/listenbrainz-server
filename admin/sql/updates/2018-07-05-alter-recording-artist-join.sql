BEGIN;

ALTER TABLE recording_artist_join DROP COLUMN artist_mbid;
ALTER TABLE recording_artist_join ADD COLUMN artist_mbids_array UUID[] NOT NULL;

COMMIT;
