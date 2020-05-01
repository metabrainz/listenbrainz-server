BEGIN;

-- Messybrainz artists are artist credits. That is, they could
-- represent more than 1 musicbrainz id. These are linked in the
-- artist_redirect table.
CREATE TABLE artist_credit (
  gid  UUID NOT NULL,
  name TEXT NOT NULL,
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE artist_credit_cluster (
  cluster_id        UUID,
  artist_credit_gid UUID, -- FK to artist_credit.gid, Not unique
  updated           TIMESTAMP WITH TIME ZONE NOT NULL
);
ALTER TABLE artist_credit_cluster ADD CONSTRAINT artist_credit_cluster_uniq UNIQUE (cluster_id, artist_credit_gid);

CREATE TABLE artist_credit_redirect (
  artist_credit_cluster_id UUID NOT NULL, -- FK to artist_credit_cluster.cluster_id
  artist_mbids             UUID[] NOT NULL
);
ALTER TABLE artist_credit_redirect ADD CONSTRAINT artist_credit_redirect_artist_mbids_uniq UNIQUE (artist_mbids);

CREATE TABLE recording (
  id         SERIAL,
  gid        UUID    NOT NULL,
  data       INTEGER NOT NULL, -- FK to recording_json.id
  artist     UUID    NOT NULL, -- FK to artist_credit.gid
  release    UUID,             -- FK to release.gid
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recording_artist_join (
  recording_mbid        UUID NOT NULL,
  artist_mbids          UUID[] NOT NULL,
  updated               TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE recording_cluster (
  cluster_id    UUID NOT NULL,
  recording_gid UUID NOT NULL, -- FK to recording.gid, Unique
  updated       TIMESTAMP WITH TIME ZONE NOT NULL
);
ALTER TABLE recording_cluster ADD CONSTRAINT recording_cluster_uniq UNIQUE (cluster_id, recording_gid);

CREATE TABLE recording_json (
  id          SERIAL,
  data        JSONB    NOT NULL,
  data_sha256 CHAR(64) NOT NULL,
  meta_sha256 CHAR(64) NOT NULL
);

CREATE TABLE recording_redirect (
  recording_cluster_id UUID NOT NULL,
  recording_mbid       UUID NOT NULL
);
ALTER TABLE recording_redirect ADD CONSTRAINT recording_redirect_uniq UNIQUE (recording_cluster_id, recording_mbid);

CREATE TABLE recording_release_join (
  recording_mbid UUID NOT NULL,
  release_mbid   UUID NOT NULL,
  release_name   TEXT NOT NULL,
  updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE release (
  gid   UUID NOT NULL,
  title TEXT NOT NULL,
  submitted  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE release_cluster (
  cluster_id  UUID,
  release_gid UUID, -- FK to release.gid, Unique
  updated     TIMESTAMP WITH TIME ZONE NOT NULL
);
ALTER TABLE release_cluster ADD CONSTRAINT release_cluster_uniq UNIQUE (cluster_id, release_gid);

CREATE TABLE release_redirect (
  release_cluster_id UUID NOT NULL, --FK to release_cluster.cluster_id
  release_mbid       UUID NOT NULL
);
ALTER TABLE release_redirect ADD CONSTRAINT release_redirect_uniq UNIQUE (release_cluster_id, release_mbid);

COMMIT;
