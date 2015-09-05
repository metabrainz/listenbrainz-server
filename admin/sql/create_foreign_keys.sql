BEGIN;

ALTER TABLE highlevel
  ADD CONSTRAINT highlevel_fk_lowlevel
  FOREIGN KEY (id)
  REFERENCES lowlevel (id);

ALTER TABLE highlevel
  ADD CONSTRAINT highlevel_fk_highlevel_json
  FOREIGN KEY (data)
  REFERENCES highlevel_json (id);

ALTER TABLE dataset
  ADD CONSTRAINT dataset_fk_user
  FOREIGN KEY (author)
  REFERENCES "user" (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_class
  ADD CONSTRAINT class_fk_dataset
  FOREIGN KEY (dataset)
  REFERENCES dataset (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_class_member
  ADD CONSTRAINT class_member_fk_class
  FOREIGN KEY (class)
  REFERENCES dataset_class (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

ALTER TABLE dataset_eval_jobs
  ADD CONSTRAINT dataset_eval_jobs_fk_dataset
  FOREIGN KEY (dataset_id)
  REFERENCES dataset (id)
  ON UPDATE CASCADE
  ON DELETE CASCADE;

COMMIT;
