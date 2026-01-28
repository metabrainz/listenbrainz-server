BEGIN;

ALTER TABLE external_service_oauth ALTER COLUMN access_token DROP NOT NULL;

COMMIT;
