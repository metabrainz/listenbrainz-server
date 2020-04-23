BEGIN;

ALTER TABLE recording
  ADD CONSTRAINT recording_fk_recording_json
  FOREIGN KEY (data)
  REFERENCES recording_json (id);

ALTER TABLE recording_cluster
  ADD CONSTRAINT recording_cluster_fk_recording
  FOREIGN KEY (recording_gid)
    REFERENCES recording (gid);

COMMIT;
