BEGIN;

ALTER TABLE scribble ADD CONSTRAINT highlevel_pkey PRIMARY KEY (id);
ALTER TABLE scribble_json ADD CONSTRAINT highlevel_json_pkey PRIMARY KEY (id);

COMMIT;
