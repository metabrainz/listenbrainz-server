BEGIN;

CREATE TABLE recording_artist_join (
  recording_mbid UUID NOT NULL,
  artist_mbid UUID NOT NULL,
  updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX mbid_ndx_recording ON recording_artist_join (recording_mbid);

COMMIT;
