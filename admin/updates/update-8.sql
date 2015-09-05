BEGIN;

ALTER TABLE dataset_eval_jobs ADD COLUMN status_msg VARCHAR;

COMMIT;
