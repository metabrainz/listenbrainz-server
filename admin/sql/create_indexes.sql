BEGIN;

CREATE INDEX data_recording ON recording (data);

CREATE UNIQUE INDEX data_sha256_ndx_recording_json ON recording_json (data_sha256);
CREATE INDEX meta_sha256_ndx_recording_json ON recording_json (meta_sha256);
CREATE UNIQUE INDEX gid_ndx_recording ON recording (gid);

CREATE INDEX gid_ndx_recording_cluster ON recording_cluster (recording_gid);
CREATE UNIQUE INDEX cluster_id_ndx_recording_cluster ON recording_cluster (cluster_id);

CREATE INDEX gid_ndx_artist_credit_cluster ON artist_credit_cluster (artist_credit_gid);
CREATE UNIQUE INDEX cluster_id_ndx_artist_credit_cluster ON artist_credit_cluster (cluster_id);

CREATE INDEX gid_ndx_release_cluster ON release_cluster (release_gid);
CREATE UNIQUE INDEX cluster_id_ndx_release_cluster ON release_cluster (cluster_id);

CREATE INDEX name_ndx_artist_credit ON artist_credit (name);
CREATE INDEX title_ndx_release ON release (title);

CREATE INDEX mbid_ndx_recording ON recording_artist_join (recording_mbid);

COMMIT;
