BEGIN;

TRUNCATE TABLE external_service_oauth;

ALTER TABLE external_service_oauth ADD COLUMN scopes TEXT[];
ALTER TABLE external_service_oauth DROP COLUMN service_details;
COMMIT;