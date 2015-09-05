BEGIN;

ALTER TABLE lowlevel ADD CONSTRAINT lowlevel_pkey PRIMARY KEY (id);
ALTER TABLE highlevel ADD CONSTRAINT highlevel_pkey PRIMARY KEY (id);
ALTER TABLE highlevel_json ADD CONSTRAINT highlevel_json_pkey PRIMARY KEY (id);
ALTER TABLE statistics ADD CONSTRAINT statistics_pkey PRIMARY KEY (name, collected);
ALTER TABLE incremental_dumps ADD CONSTRAINT incremental_dumps_pkey PRIMARY KEY (id);
ALTER TABLE "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE dataset ADD CONSTRAINT dataset_pkey PRIMARY KEY (id);
ALTER TABLE dataset_class ADD CONSTRAINT dataset_class_pkey PRIMARY KEY (id);
ALTER TABLE dataset_class_member ADD CONSTRAINT dataset_class_member_pkey PRIMARY KEY (class, mbid);
ALTER TABLE dataset_eval_jobs ADD CONSTRAINT dataset_eval_jobs_pkey PRIMARY KEY (id);

COMMIT;
