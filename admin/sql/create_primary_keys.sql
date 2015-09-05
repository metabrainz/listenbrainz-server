BEGIN;

ALTER TABLE scribble ADD CONSTRAINT scribble_pkey PRIMARY KEY (id);
ALTER TABLE scribble_json ADD CONSTRAINT scribble_json_pkey PRIMARY KEY (id);

ALTER TABLE scribble ADD CONSTRAINT scribble_gid_unique UNIQUE (gid);

COMMIT;
