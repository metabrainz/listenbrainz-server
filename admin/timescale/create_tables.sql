BEGIN;

CREATE TABLE listen (
    listened_at     TIMESTAMP WITH TIME ZONE NOT NULL,
    created         TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    user_id         INTEGER                  NOT NULL,
    recording_msid  UUID                     NOT NULL,
    data            JSONB                    NOT NULL
);

CREATE TABLE listen_user_metadata (
    user_id             INTEGER                     NOT NULL,
    count               BIGINT                      NOT NULL, -- count of listens the user has earlier than `created`
    min_listened_at     TIMESTAMP WITH TIME ZONE, -- minimum listened_at timestamp seen for the user in listens till `created`
    max_listened_at     TIMESTAMP WITH TIME ZONE, -- maximum listened_at timestamp seen for the user in listens till `created`
    created             TIMESTAMP WITH TIME ZONE    NOT NULL  -- the created timestamp when data for this user was updated last
);

SELECT create_hypertable('listen', 'listened_at', chunk_time_interval => INTERVAL '30 days');

COMMIT;
