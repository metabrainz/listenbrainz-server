BEGIN;

CREATE UNIQUE INDEX data_sha256_ndx_scribble_json ON scribble_json (data_sha256);
CREATE INDEX gid_ndx_scribble ON scribble (gid);

COMMIT;
