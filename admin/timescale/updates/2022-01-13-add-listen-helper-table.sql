BEGIN;
CREATE TABLE listen_user_metadata (
    user_id             INTEGER                     NOT NULL,
    count               BIGINT                      NOT NULL, -- count of listens the user has earlier than `created`
    min_listened_at     BIGINT, -- minimum listened_at timestamp seen for the user in listens till `created`
    max_listened_at     BIGINT, -- maximum listened_at timestamp seen for the user in listens till `created`
    created             TIMESTAMP WITH TIME ZONE    NOT NULL  -- the created timestamp when data for this user was updated last
);
CREATE UNIQUE INDEX user_id_ndx_user_metadata ON listen_user_metadata (user_id);
COMMIT;
