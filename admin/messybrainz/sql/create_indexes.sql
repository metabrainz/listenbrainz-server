BEGIN;

CREATE INDEX data_recording ON recording (data);

CREATE UNIQUE INDEX data_sha256_ndx_recording_json ON recording_json (data_sha256);
CREATE INDEX meta_sha256_ndx_recording_json ON recording_json (meta_sha256);
CREATE UNIQUE INDEX gid_ndx_recording ON recording (gid);

CREATE INDEX name_ndx_artist_credit ON artist_credit (name);
CREATE INDEX title_ndx_release ON release (title);

CREATE INDEX recording_mbid_ndx_recording_json ON recording_json ((data ->> 'recording_mbid'));
CREATE INDEX artist_mbid_ndx_recording_json ON recording_json ((data ->> 'artist_mbids'));
CREATE INDEX release_mbid_ndx_recording_json ON recording_json ((data ->> 'release_mbid'));
CREATE INDEX artist_mbid_array_ndx_recording_json ON recording_json (convert_json_array_to_sorted_uuid_array((data -> 'artist_mbids')));

CREATE INDEX artist_ndx_recording ON recording (artist);
CREATE INDEX release_ndx_recording ON recording (release);

COMMIT;
