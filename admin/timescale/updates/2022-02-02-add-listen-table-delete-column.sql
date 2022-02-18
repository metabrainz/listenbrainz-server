BEGIN;
CREATE TABLE listen_delete_metadata (
    id                  SERIAL                      NOT NULL,
    user_id             INTEGER                     NOT NULL,
    listened_at         BIGINT                      NOT NULL,
    recording_msid      UUID                        NOT NULL
);
COMMIT;
