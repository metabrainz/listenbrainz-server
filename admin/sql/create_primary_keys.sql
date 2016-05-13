BEGIN;

ALTER TABLE "user" ADD CONSTRAINT user_pkey PRIMARY KEY (id);
ALTER TABLE listens ADD CONSTRAINT listens_pkey PRIMARY KEY (uid, timestamp);

COMMIT;
