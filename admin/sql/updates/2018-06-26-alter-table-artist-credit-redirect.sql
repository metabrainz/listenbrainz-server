BEGIN;

ALTER TABLE artist_credit_redirect DROP COLUMN artist_mbid;
ALTER TABLE artist_credit_redirect ADD COLUMN artist_mbids_array UUID[] NOT NULL;

COMMIT;