BEGIN;

ALTER TABLE recording ADD CONSTRAINT recording_pkey PRIMARY KEY (id);
ALTER TABLE recording_json ADD CONSTRAINT recording_json_pkey PRIMARY KEY (id);

ALTER TABLE artist_credit ADD CONSTRAINT artist_credit_pkey PRIMARY KEY (gid);
ALTER TABLE release ADD CONSTRAINT release_pkey PRIMARY KEY (gid);

ALTER TABLE recording ADD CONSTRAINT recording_gid_unique UNIQUE (gid);

COMMIT;
