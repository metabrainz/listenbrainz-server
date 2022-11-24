BEGIN;

CREATE SCHEMA mapping;

-- this table is defined in listenbrainz/mbid_mapping/mapping/mb_metadata_cache.py and created in production
-- there. this definition is only for tests and local development. remember to keep both in sync.
CREATE TABLE mapping.mb_metadata_cache (
    dirty               BOOLEAN DEFAULT FALSE,
    recording_mbid      UUID NOT NULL,
    artist_mbids        UUID[] NOT NULL,
    release_mbid        UUID,
    recording_data      JSONB NOT NULL,
    artist_data         JSONB NOT NULL,
    tag_data            JSONB NOT NULL,
    release_data        JSONB NOT NULL
);

ALTER TABLE mapping.mb_metadata_cache ADD CONSTRAINT mb_metadata_cache_pkey PRIMARY KEY (recording_mbid);

-- postgres does not enforce dimensionality of arrays. add explicit check to avoid regressions (once burnt, twice shy!).
ALTER TABLE mapping.mb_metadata_cache
    ADD CONSTRAINT mb_metadata_cache_artist_mbids_check
    CHECK ( array_ndims(artist_mbids) = 1 );

CREATE UNIQUE INDEX mb_metadata_cache_idx_recording_mbid ON mapping.mb_metadata_cache (recording_mbid);
CREATE INDEX mb_metadata_cache_idx_artist_mbids ON mapping.mb_metadata_cache USING gin(artist_mbids);
CREATE INDEX mb_metadata_cache_idx_dirty ON mapping.mb_metadata_cache (dirty);

-- no FK because mb_metadata_cache is rebuilt from scratch at regular intervals
-- drop FK from mbid_mapping_metadata because the table is no longer used in development or test
ALTER TABLE mbid_mapping DROP CONSTRAINT mbid_mapping_recording_mbid_foreign_key;
COMMIT;
