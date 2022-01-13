BEGIN;
CREATE TABLE listen_count(
    user_id         INTEGER                     NOT NULL,
    count           BIGINT                      NOT NULL,
    timestamp       TIMESTAMP WITH TIME ZONE    NOT NULL  -- timestamp of the latest `created` listen for the user
);
CREATE UNIQUE INDEX user_id_ndx_listen_count ON listen_count (user_id);
COMMIT;
