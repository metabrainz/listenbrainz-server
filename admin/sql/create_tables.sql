BEGIN;

CREATE TABLE "user" (
  id                    SERIAL,
  created               TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  musicbrainz_id        VARCHAR NOT NULL,
  auth_token            VARCHAR,
  last_login            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  latest_import         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT TIMESTAMP 'epoch',
  gdpr_agreed           TIMESTAMP WITH TIME ZONE,
  musicbrainz_row_id    INTEGER NOT NULL,
  login_id              TEXT NOT NULL DEFAULT uuid_generate_v4()::text
);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_id_key UNIQUE (musicbrainz_id);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_row_id_key UNIQUE (musicbrainz_row_id);
ALTER TABLE "user" ADD CONSTRAINT user_login_id_key UNIQUE (login_id);

CREATE TABLE spotify_auth (
  user_id                   INTEGER NOT NULL, -- PK and FK to user.id
  user_token                VARCHAR NOT NULL,
  token_expires             TIMESTAMP WITH TIME ZONE,
  refresh_token             VARCHAR NOT NULL,
  last_updated              TIMESTAMP WITH TIME ZONE,
  latest_listened_at        TIMESTAMP WITH TIME ZONE,
  record_listens            BOOLEAN DEFAULT TRUE,
  error_message             VARCHAR,
  permission                VARCHAR NOT NULL
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
    artist                  JSONB,
    release                 JSONB,
    recording               JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE statistics.artist (
    id                      SERIAL, -- PK
    msid                    UUID NOT NULL,
    name                    VARCHAR,
    release                 JSONB,
    recording               JSONB,
    listener                JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
ALTER TABLE statistics.artist ADD CONSTRAINT artist_stats_msid_uniq UNIQUE (msid);

CREATE TABLE statistics.release (
    id                      SERIAL, -- PK
    msid                    UUID NOT NULL,
    name                    VARCHAR,
    recording               JSONB,
    listener                JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
ALTER TABLE statistics.release ADD CONSTRAINT release_stats_msid_uniq UNIQUE (msid);

CREATE TABLE statistics.recording (
    id                      SERIAL, -- PK
    msid                    UUID NOT NULL,
    name                    VARCHAR,
    listener                JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()

);
ALTER TABLE statistics.recording ADD CONSTRAINT recording_stats_msid_uniq UNIQUE (msid);

CREATE TABLE data_dump (
  id          SERIAL,
  created     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE follow_list (
  id                SERIAL, -- PK
  name              TEXT NOT NULL,
  creator           INTEGER NOT NULL, -- FK to "user".id
  private           BOOLEAN NOT NULL DEFAULT FALSE,
  members           INTEGER ARRAY NOT NULL DEFAULT ARRAY[]::INTEGER[],
  created           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  last_saved        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
ALTER TABLE follow_list ADD CONSTRAINT follow_list_name_creator_key UNIQUE (name, creator);

COMMIT;
