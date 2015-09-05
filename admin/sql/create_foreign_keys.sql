BEGIN;

ALTER TABLE scribble
  ADD CONSTRAINT scribble_fk_scribble_json
  FOREIGN KEY (data)
  REFERENCES scribble_json (id);

ALTER TABLE scribble_cluster
  ADD CONSTRAINT scribble_cluster_fk_scribble
  FOREIGN KEY (gid)
    REFERENCES scribble (gid);

COMMIT;
