BEGIN;

CREATE TABLE "user" (
  id             SERIAL,
  created        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  musicbrainz_id VARCHAR NOT NULL,
  auth_token     VARCHAR,
  last_login     TIMESTAMP WITH TIME ZONE
);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_id_key UNIQUE (musicbrainz_id);

CREATE TABLE listen (
  id              SERIAL,
  user_id         INTEGER NOT NULL, -- FK to user.name
  ts              TIMESTAMP WITH TIME ZONE NOT NULL,
  artist_msid     UUID NOT NULL,
  release_msid    UUID,
  recording_msid  UUID NOT NULL
);
ALTER TABLE listen ADD CONSTRAINT listen_id_uniq UNIQUE (id);

CREATE TABLE listen_json (
  id              INTEGER NOT NULL, -- FK to listen.id
  data            JSONB NOT NULL
);

CREATE TABLE api_compat.token (
     id               SERIAL,
     user_id          INTEGER, -- FK to "user".id
     token            TEXT NOT NULL,
     api_key          VARCHAR NOT NULL,
     ts               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE api_compat.token ADD CONSTRAINT token_api_key_uniq UNIQUE (api_key);
ALTER TABLE api_compat.token ADD CONSTRAINT token_token_uniq UNIQUE (token);

CREATE TABLE api_compat.session (
    id        SERIAL,
    user_id   INTEGER NOT NULL, -- FK to "user".id
    sid       VARCHAR NOT NULL,
    api_key   VARCHAR NOT NULL,
    ts        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE api_compat.session ADD CONSTRAINT session_sid_uniq UNIQUE (sid);

CREATE TABLE statistics.user (
    user_id                 INTEGER NOT NULL, -- PK and FK to "user".id
    artists                 JSONB,
    releases                JSONB,
    recordings              JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE
);
ALTER TABLE statistics.user ADD CONSTRAINT user_stats_user_id_uniq UNIQUE (user_id);

CREATE TABLE statistics.artist (
    id                      SERIAL, -- PK
    msid                    UUID NOT NULL,
    name                    VARCHAR,
    releases                JSONB,
    recordings              JSONB,
    users                   JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE
);
ALTER TABLE statistics.artist ADD CONSTRAINT artist_stats_msid_uniq UNIQUE (msid);

CREATE TABLE statistics.release (
    id                      SERIAL, -- PK
    msid                    UUID NOT NULL,
    name                    VARCHAR,
    recordings              JSONB,
    users                   JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE
);
ALTER TABLE statistics.release ADD CONSTRAINT release_stats_msid_uniq UNIQUE (msid);

CREATE TABLE statistics.recording (
    id                      SERIAL, -- PK
    msid                    UUID NOT NULL,
    name                    VARCHAR,
    users_all_time          JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE

);
ALTER TABLE statistics.recording ADD CONSTRAINT recording_stats_msid_uniq UNIQUE (msid);

COMMIT;
