
BEGIN;

ALTER TABLE user_setting
ADD brainzplayer JSONB;

COMMIT;