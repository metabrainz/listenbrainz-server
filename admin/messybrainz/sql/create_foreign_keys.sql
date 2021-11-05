BEGIN;

ALTER TABLE recording
  ADD CONSTRAINT recording_fk_recording_json
  FOREIGN KEY (data)
  REFERENCES recording_json (id);

COMMIT;
