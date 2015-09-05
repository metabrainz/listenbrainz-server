BEGIN;

CREATE UNIQUE INDEX data_sha256_ndx_scribble_json ON scribble_json (data_sha256);
CREATE UNIQUE INDEX gid_ndx_scribble ON scribble (gid);

CREATE UNIQUE INDEX gid_ndx_scribble_cluster ON scribble_cluster (gid);
CREATE UNIQUE INDEX cluster_id_ndx_scribble_cluster ON scribble_cluster (cluster_id);

COMMIT;
