BEGIN;
CREATE TABLE listen_helper (
    user_id             INTEGER                     NOT NULL,
    count               BIGINT                      NOT NULL, -- count of listens the user has earlier than `created`
    min_listened_at     BIGINT                      NOT NULL, -- minimum listened_at timestamp seen for the user in listens till `created`
    max_listened_at     BIGINT                      NOT NULL, -- maximum listened_at timestamp seen for the user in listens till `created`
    created             TIMESTAMP WITH TIME ZONE    NOT NULL  -- the created timestamp when data for this user was updated last
);
CREATE UNIQUE INDEX user_id_ndx_listen_count ON listen_count (user_id);
COMMIT;
