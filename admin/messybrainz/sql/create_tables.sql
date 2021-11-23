BEGIN;

-- Messybrainz artists are artist credits. That is, they could
-- represent more than 1 musicbrainz id. These are linked in the
-- artist_redirect table.
CREATE TABLE artist_credit (
  gid  UUID NOT NULL,
  name TEXT NOT NULL,
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recording (
  id         SERIAL,
  gid        UUID    NOT NULL,
  data       INTEGER NOT NULL, -- FK to recording_json.id
  artist     UUID    NOT NULL, -- FK to artist_credit.gid
  release    UUID,             -- FK to release.gid
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recording_json (
  id          SERIAL,
  data        JSONB    NOT NULL,
  data_sha256 CHAR(64) NOT NULL,
  meta_sha256 CHAR(64) NOT NULL
);

CREATE TABLE release (
  gid   UUID NOT NULL,
  title TEXT NOT NULL,
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMIT;
