BEGIN;

-- Drop indexes and recreate them to remove UNIQUE constraint
DROP INDEX IF EXISTS cluster_id_ndx_recording_cluster;
DROP INDEX IF EXISTS cluster_id_ndx_artist_credit_cluster;
DROP INDEX IF EXISTS cluster_id_ndx_release_cluster;

CREATE INDEX cluster_id_ndx_recording_cluster ON recording_cluster (cluster_id);
CREATE INDEX cluster_id_ndx_artist_credit_cluster ON artist_credit_cluster (cluster_id);
CREATE INDEX cluster_id_ndx_release_cluster ON release_cluster (cluster_id);

-- Add UNIQUE constraints so that we don't get duplicate entries in tables
ALTER TABLE recording_cluster ADD CONSTRAINT recording_cluster_uniq UNIQUE (cluster_id, recording_gid);
ALTER TABLE recording_redirect ADD CONSTRAINT recording_redirect_uniq UNIQUE (recording_cluster_id, recording_mbid);

ALTER TABLE artist_credit_cluster ADD CONSTRAINT artist_credit_cluster_uniq UNIQUE (cluster_id, artist_credit_gid);
ALTER TABLE artist_credit_redirect ADD CONSTRAINT artist_credit_redirect_uniq UNIQUE (artist_credit_cluster_id, artist_mbid);

ALTER TABLE release_cluster ADD CONSTRAINT release_cluster_uniq UNIQUE (cluster_id, release_gid);
ALTER TABLE release_redirect ADD CONSTRAINT release_redirect_uniq UNIQUE (release_cluster_id, release_mbid);

COMMIT;
