BEGIN;

CREATE TYPE eval_job_status AS ENUM ('pending', 'running', 'done', 'failed');

CREATE TABLE dataset_eval_jobs (
  id         UUID,
  dataset_id UUID                     NOT NULL,
  status     eval_job_status          NOT NULL DEFAULT 'pending',
  result     JSON,
  created    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE dataset_eval_jobs ADD CONSTRAINT dataset_eval_jobs_pkey PRIMARY KEY (id);

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_dataset
  FOREIGN KEY (dataset_id)
  REFERENCES dataset (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

COMMIT;
