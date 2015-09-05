BEGIN;

ALTER TABLE scribble
  ADD CONSTRAINT scribble_fk_highlevel_json
  FOREIGN KEY (data)
  REFERENCES scribble_json (id);

COMMIT;
