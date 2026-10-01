BEGIN;

ALTER TABLE user_data_export
    ADD COLUMN start_time BIGINT,
    ADD COLUMN end_time BIGINT;

COMMIT;
