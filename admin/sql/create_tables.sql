BEGIN;

CREATE TABLE scribble (
  id         SERIAL,
  gid        UUID    NOT NULL,
  data       INTEGER NOT NULL, -- FK to scribble_json.id
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE scribble_json (
  id          SERIAL,
  data        JSON     NOT NULL,
  data_sha256 CHAR(64) NOT NULL
);

CREATE TABLE redirect (
  cluster_id  UUID              NOT NULL,
  musicbrainz_recording_id UUID NOT NULL
);

CREATE TABLE scribble_cluster (
  cluster_id  UUID NOT NULL,
  gid         UUID NOT NULL -- FK to scribble.gid
);

COMMIT;
