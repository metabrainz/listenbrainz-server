BEGIN;

CREATE TABLE recording_release_join (
  recording_mbid UUID NOT NULL,
  release_mbid   UUID NOT NULL,
  release_name   TEXT NOT NULL,
  updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMIT;
