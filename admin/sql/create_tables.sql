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

CREATE TABLE api_compat.session (
    id        SERIAL,
    user_id   INTEGER NOT NULL, -- FK to "user".id
    sid       VARCHAR NOT NULL,
    api_key   VARCHAR NOT NULL,
    ts        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE api_compat.session ADD CONSTRAINT session_sid_uniq UNIQUE (sid);

CREATE TABLE api_compat.token (
     id               SERIAL,
     user_id          INTEGER, -- FK to "user".id
     token            TEXT NOT NULL,
     api_key          VARCHAR NOT NULL,
     ts               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE api_compat.token ADD CONSTRAINT token_api_key_uniq UNIQUE (api_key);
ALTER TABLE api_compat.token ADD CONSTRAINT token_token_uniq UNIQUE (token);

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

CREATE TABLE missing_musicbrainz_data (
    id              SERIAL, -- PK
    user_id         INTEGER NOT NULL, --FK to "user".id
    data            JSONB NOT NULL,
    source          MB_MISSING_DATA_SOURCE_ENUM NOT NULL,
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
ALTER TABLE missing_musicbrainz_data ADD CONSTRAINT user_id_unique UNIQUE (user_id);

CREATE TABLE recommendation.cf_recording (
  id                  SERIAL, -- PK
  user_id             INTEGER NOT NULL, --FK to "user".id
  recording_mbid      JSONB NOT NULL,
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);
ALTER TABLE recommendation.cf_recording ADD CONSTRAINT user_id_unique UNIQUE (user_id);

CREATE TABLE recommendation.recommender (
  id                  SERIAL, --PK
  user_id             INTEGER NOT NULL, --FK to "user".id, denotes user who wrote software for this recommender.
  repository          TEXT NOT NULL,
  name                TEXT NOT NULL,
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE recommendation.recommender_session (
  id                  SERIAL, --PK
  recommender_id      INTEGER NOT NULL, --FK to recommendation.recommender.id
  user_id             INTEGER NOT NULL, --FK to "user".id, user for whom the recommendations are generated.
  created             TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  data                JSONB
);

CREATE TABLE recommendation.recording_session (
  last_used           TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  recording_msid      UUID NOT NULL,
  session_id          INTEGER NOT NULL --FK to recommendation.recommender_session.id
);

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

CREATE TABLE statistics.user (
    user_id                 INTEGER NOT NULL, -- PK and FK to "user".id
    artist                  JSONB,
    release                 JSONB,
    recording               JSONB,
    listening_activity      JSONB,
    daily_activity          JSONB,
    artist_map              JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE statistics.sitewide (
    id                      SERIAL, --pk
    stats_range             TEXT,
    artist                  JSONB,
    release                 JSONB,
    recording               JSONB,
    listening_activity      JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE statistics.sitewide ADD CONSTRAINT stats_range_uniq UNIQUE (stats_range);

CREATE TABLE recommendation_feedback (
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    recording_mbid          UUID NOT NULL,
    rating                  recommendation_feedback_type_enum NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE recording_feedback (
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    recording_msid          UUID NOT NULL,
    score                   SMALLINT NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE user_relationship (
    -- relationships go from 0 to 1
    -- for example, if relationship type is "follow", then user_0 follows user_1
    user_0              INTEGER NOT NULL, -- FK to "user".id
    user_1              INTEGER NOT NULL, -- FK to "user".id
    relationship_type   user_relationship_enum NOT NULL,
    created             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO listenbrainz;

COMMIT;
