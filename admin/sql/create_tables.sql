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
  login_id              TEXT NOT NULL DEFAULT uuid_generate_v4()::text,
  email                 TEXT
);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_id_key UNIQUE (musicbrainz_id);
ALTER TABLE "user" ADD CONSTRAINT user_musicbrainz_row_id_key UNIQUE (musicbrainz_row_id);
ALTER TABLE "user" ADD CONSTRAINT user_login_id_key UNIQUE (login_id);

CREATE TABLE reported_users (
    id                  SERIAL,
    reporter_user_id    INTEGER NOT NULL, -- FK to "user".id of the user who reported
    reported_user_id    INTEGER NOT NULL, -- FK to "user".id of the user who was reported
    reported_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason              TEXT
);

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

CREATE TABLE recommendation.similar_user (
  user_id         INTEGER NOT NULL, -- FK to "user".id
  similar_users   JSONB,
  last_updated    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE user_timeline_event (
  id                    SERIAL, -- PK
  user_id               INTEGER, -- FK to "user"
  event_type            user_timeline_event_type_enum,
  metadata              JSONB,
  created               TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE hide_user_timeline_event (
    id           SERIAL NOT NULL,  --PK
    user_id      INTEGER NOT NULL, --FK to "user"
    event_type   hide_user_timeline_event_type_enum NOT NULL,
    event_id     INTEGER NOT NULL, --Row ID of recommendation or pin
    created      TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
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

CREATE TABLE external_service_oauth (
    id                      SERIAL,  -- PK
    user_id                 INTEGER NOT NULL,  -- FK to "user".id
    service                 external_service_oauth_type NOT NULL,
    access_token            TEXT NOT NULL,
    refresh_token           TEXT,
    token_expires           TIMESTAMP WITH TIME ZONE,
    last_updated            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    scopes                  TEXT[]
);

CREATE TABLE listens_importer (
    id                          SERIAL,  -- PK
    external_service_oauth_id   INTEGER, -- FK to external_service_oauth.id
    user_id                     INTEGER NOT NULL,  -- FK to "user".id
    service                     external_service_oauth_type NOT NULL,
    last_updated                TIMESTAMP WITH TIME ZONE,
    latest_listened_at          TIMESTAMP WITH TIME ZONE,
    error_message               TEXT
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
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    stats_type              user_stats_type,
    stats_range             stats_range_type,
    data                    JSONB,
    count                   INTEGER,
    -- we use int timestamps when serializing data in spark, we return the same from the api
    -- using timestamp with time zone here just complicates stuff. we'll need to add
    -- datetime/timestamp conversions in code at multiple places and we never seem to use this
    -- value anyways in LB backend atm.
    from_ts                 BIGINT,
    to_ts                   BIGINT,
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

CREATE TABLE statistics.year_in_music (
    user_id     INTEGER NOT NULL, -- FK to "user".id
    data        JSONB
);


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
    recording_msid          UUID,
    recording_mbid          UUID,
    score                   SMALLINT NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE recording_feedback
    ADD CONSTRAINT feedback_recording_msid_or_recording_mbid_check
    CHECK ( recording_msid IS NOT NULL OR recording_mbid IS NOT NULL );

CREATE TABLE release_color(
    id                      SERIAL, -- PK
    caa_id                  BIGINT NOT NULL,
    release_mbid            UUID NOT NULL,
    red                     SMALLINT NOT NULL,
    green                   SMALLINT NOT NULL,
    blue                    SMALLINT NOT NULL,
    color                   CUBE,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE user_relationship (
    -- relationships go from 0 to 1
    -- for example, if relationship type is "follow", then user_0 follows user_1
    user_0              INTEGER NOT NULL, -- FK to "user".id
    user_1              INTEGER NOT NULL, -- FK to "user".id
    relationship_type   user_relationship_enum NOT NULL,
    created             TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE pinned_recording(
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    recording_msid          UUID,
    recording_mbid          UUID,
    blurb_content           TEXT,
    pinned_until            TIMESTAMP WITH TIME ZONE NOT NULL,
    created                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE pinned_recording
    ADD CONSTRAINT pinned_rec_recording_msid_or_recording_mbid_check
    CHECK ( recording_msid IS NOT NULL OR recording_mbid IS NOT NULL );

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO listenbrainz;

COMMIT;
