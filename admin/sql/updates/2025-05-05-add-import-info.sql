BEGIN;

ALTER TABLE "listens_importer" ADD COLUMN status JSONB;

COMMIT;
