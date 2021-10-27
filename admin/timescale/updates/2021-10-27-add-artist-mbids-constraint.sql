BEGIN;
ALTER TABLE listen_mbid_mapping
    ADD CONSTRAINT listen_mbid_mapping_artist_mbids_check
    CHECK ( array_ndims(artist_mbids) = 1 );
COMMIT;
