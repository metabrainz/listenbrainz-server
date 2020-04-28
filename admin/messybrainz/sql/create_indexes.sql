BEGIN;

CREATE INDEX data_recording ON recording (data);

CREATE UNIQUE INDEX data_sha256_ndx_recording_json ON recording_json (data_sha256);
CREATE INDEX meta_sha256_ndx_recording_json ON recording_json (meta_sha256);
CREATE UNIQUE INDEX gid_ndx_recording ON recording (gid);

CREATE INDEX gid_ndx_recording_cluster ON recording_cluster (recording_gid);
CREATE INDEX cluster_id_ndx_recording_cluster ON recording_cluster (cluster_id);

CREATE INDEX gid_ndx_artist_credit_cluster ON artist_credit_cluster (artist_credit_gid);
CREATE INDEX cluster_id_ndx_artist_credit_cluster ON artist_credit_cluster (cluster_id);

CREATE INDEX gid_ndx_release_cluster ON release_cluster (release_gid);
CREATE INDEX cluster_id_ndx_release_cluster ON release_cluster (cluster_id);

CREATE INDEX name_ndx_artist_credit ON artist_credit (name);
CREATE INDEX title_ndx_release ON release (title);

CREATE INDEX recording_mbid_ndx_recording_artist_join ON recording_artist_join (recording_mbid);
CREATE INDEX artist_mbids_ndx_recording_artist_join ON recording_artist_join (artist_mbids);

CREATE INDEX recording_mbid_ndx_recording_redirect ON recording_redirect (recording_mbid);
CREATE INDEX artist_mbids_array_ndx_artist_credit_redirect ON artist_credit_redirect (artist_mbids);
CREATE INDEX release_mbid_ndx_recording_redirect ON release_redirect (release_mbid);

CREATE INDEX recording_cluster_id_ndx_recording_redirect ON recording_redirect (recording_cluster_id);
CREATE INDEX artist_credit_cluster_id_ndx_artist_credit_redirect ON artist_credit_redirect (artist_credit_cluster_id);
CREATE INDEX release_cluster_id_ndx_recording_redirect ON release_redirect (release_cluster_id);

CREATE INDEX recording_mbid_ndx_recording_json ON recording_json ((data ->> 'recording_mbid'));
CREATE INDEX artist_mbid_ndx_recording_json ON recording_json ((data ->> 'artist_mbids'));
CREATE INDEX release_mbid_ndx_recording_json ON recording_json ((data ->> 'release_mbid'));
CREATE INDEX artist_mbid_array_ndx_recording_json ON recording_json (convert_json_array_to_sorted_uuid_array((data -> 'artist_mbids')));

CREATE INDEX artist_ndx_recording ON recording (artist);
CREATE INDEX release_ndx_recording ON recording (release);

CREATE INDEX recording_mbid_ndx_recording_release_join ON recording_release_join (recording_mbid);
CREATE INDEX release_mbid_ndx_recording_release_join ON recording_release_join (release_mbid);
CREATE INDEX release_name_ndx_recording_release_join ON recording_release_join (release_name);

COMMIT;
