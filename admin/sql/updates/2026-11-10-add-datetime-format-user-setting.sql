BEGIN;

ALTER TABLE user_setting ADD COLUMN datetime_format JSONB;

COMMIT;
