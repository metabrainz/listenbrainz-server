BEGIN;

CREATE TABLE "user" (
  id             SERIAL,
  created        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  musicbrainz_id VARCHAR NOT NULL,
  auth_token     VARCHAR
);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_id_key UNIQUE (musicbrainz_id);

CREATE TABLE listen (
  id              SERIAL,
  user_id         VARCHAR NOT NULL,
  ts              TIMESTAMP WITH TIME ZONE NOT NULL,
  artist_msid     UUID NOT NULL,
  album_msid      UUID,
  recording_msid  UUID NOT NULL,
  raw_data        JSONB
);

CREATE TABLE token (
     id               SERIAL,
     user_id          INT,
     token            TEXT NOT NULL,
     api_key          VARCHAR NOT NULL,
     ts               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE token ADD CONSTRAINT token_api_key_uniq UNIQUE (api_key);

CREATE TABLE session (
    id        SERIAL,
    user_id   INT NOT NULL,
    sid       VARCHAR NOT NULL,
    token     VARCHAR NOT NULL,
    api_key   VARCHAR NOT NULL,
    ts        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE session ADD CONSTRAINT session_sid_token_apikey_uniq UNIQUE (user_id, token, api_key);
COMMIT;
