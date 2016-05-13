BEGIN;

CREATE TABLE "user" (
  id             SERIAL,
  created        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  musicbrainz_id VARCHAR NOT NULL,
  auth_token     VARCHAR
);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_id_key UNIQUE (musicbrainz_id);

CREATE TABLE listens (
  uid             VARCHAR NOT NULL,
  year            INT,
  month           INT,
  day             INT,
  id              INT NOT NULL,
  artist_msid     UUID,
  album_msid      UUID,
  recording_msid  UUID,
  json            VARCHAR,
  PRIMARY KEY(uid, id)
);


COMMIT;
