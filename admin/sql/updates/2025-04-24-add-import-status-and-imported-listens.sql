BEGIN;

ALTER TABLE "external_service_oauth" ADD COLUMN import_status TEXT NOT NULL DEFAULT 'queued';
ALTER TABLE "external_service_oauth" ADD COLUMN imported_listens INTEGER NOT NULL DEFAULT 0;

COMMIT;