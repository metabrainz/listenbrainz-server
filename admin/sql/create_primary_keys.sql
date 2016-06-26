BEGIN;

ALTER TABLE "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE listen ADD CONSTRAINT listen_pkey PRIMARY KEY (user_id, ts);
ALTER TABLE sessions ADD CONSTRAINT sessions_pkey PRIMARY KEY (sid);

COMMIT;
