BEGIN;
CREATE TABLE listen_delete_metadata (
    user_id             INTEGER                     NOT NULL,
    listened_at         BIGINT                      NOT NULL,
    recording_msid      UUID                        NOT NULL,
    created             TIMESTAMP WITH TIME ZONE    NOT NULL DEFAULT NOW()
);
COMMIT;
