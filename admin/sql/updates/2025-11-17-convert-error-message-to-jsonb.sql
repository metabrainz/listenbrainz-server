BEGIN;

ALTER TABLE listens_importer ADD COLUMN error JSONB;

UPDATE listens_importer
   SET error = jsonb_build_object('message', error_message, 'retry', true)
 WHERE error_message IS NOT NULL;

ALTER TABLE listens_importer DROP COLUMN error_message;

COMMIT;
