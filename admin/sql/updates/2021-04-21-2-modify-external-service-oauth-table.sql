BEGIN;

TRUNCATE TABLE external_service_oauth CASCADE;

ALTER TABLE external_service_oauth ADD COLUMN scopes TEXT[];
ALTER TABLE external_service_oauth DROP COLUMN service_details;
ALTER TABLE external_service_oauth DROP COLUMN record_listens;

COMMIT;