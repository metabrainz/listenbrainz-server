BEGIN;

CREATE TABLE scribble (
  id         SERIAL,
  gid        UUID    NOT NULL,
  data       INTEGER NOT NULL, -- FK to highlevel_json.data
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE scribble_json (
  id          SERIAL,
  data        JSON     NOT NULL,
  data_sha256 CHAR(64) NOT NULL
);

COMMIT;
