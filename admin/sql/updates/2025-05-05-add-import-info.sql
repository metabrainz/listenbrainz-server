BEGIN;

ALTER TABLE "listens_importer"
ADD COLUMN import_info JSONB;

COMMIT;