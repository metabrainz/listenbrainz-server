BEGIN;

ALTER TABLE "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE listens ADD CONSTRAINT listens_pkey PRIMARY KEY (user_id, ts);
ALTER TABLE sessions ADD CONSTRAINT sessions_pkey PRIMARY KEY (sid);

COMMIT;
