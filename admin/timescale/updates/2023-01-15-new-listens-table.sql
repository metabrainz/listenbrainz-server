BEGIN;

CREATE TABLE listen_new (
    listened_at     TIMESTAMP WITH TIME ZONE NOT NULL,
    tz_offset       INTERVAL, -- offset to apply to listened_at to get listen's local timestamp
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    user_id         INTEGER                  NOT NULL,
    recording_msid  UUID                     NOT NULL,
    data            JSONB                    NOT NULL
);

SELECT create_hypertable('listen_new', 'listened_at', chunk_time_interval => INTERVAL '30 days');

CREATE UNIQUE INDEX listened_at_user_id_recording_msid_ndx_listen ON listen_new (listened_at DESC, user_id, recording_msid);

CREATE TABLE listen_delete_metadata_new (
    id                  SERIAL                      NOT NULL,
    user_id             INTEGER                     NOT NULL,
    listened_at         TIMESTAMP WITH TIME ZONE    NOT NULL,
    recording_msid      UUID                        NOT NULL
);

CREATE TABLE listen_user_metadata_new (
    user_id             INTEGER                     NOT NULL,
    count               BIGINT                      NOT NULL, -- count of listens the user has earlier than `created`
    min_listened_at     TIMESTAMP WITH TIME ZONE, -- minimum listened_at timestamp seen for the user in listens till `created`
    max_listened_at     TIMESTAMP WITH TIME ZONE, -- maximum listened_at timestamp seen for the user in listens till `created`
    created             TIMESTAMP WITH TIME ZONE    NOT NULL  -- the created timestamp when data for this user was updated last
);
COMMIT;
