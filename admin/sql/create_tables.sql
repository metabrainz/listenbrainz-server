BEGIN;

CREATE TABLE "user" (
  id             SERIAL,
  created        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  musicbrainz_id VARCHAR NOT NULL,
  auth_token     VARCHAR
);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_id_key UNIQUE (musicbrainz_id);

CREATE TABLE listens (
  id              SERIAL,
  uid             VARCHAR NOT NULL,
  ts              TIMESTAMP WITH TIME ZONE NOT NULL,
  artist_msid     UUID,
  album_msid      UUID,
  recording_msid  UUID,
  json            VARCHAR
);

COMMIT;
