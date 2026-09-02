BEGIN;

ALTER TABLE user_setting
    ADD COLUMN submission_filters JSONB;

COMMIT;
