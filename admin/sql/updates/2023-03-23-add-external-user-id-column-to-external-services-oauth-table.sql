BEGIN;

ALTER TABLE external_service_oauth ADD COLUMN external_user_id TEXT;

COMMIT;