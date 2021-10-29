BEGIN;
ALTER TABLE listen_mbid_mapping
    ADD CONSTRAINT listen_mbid_mapping_fields_null_check
    CHECK (
        (
              match_type = 'no_match'
          AND artist_credit_id IS NULL
          AND recording_mbid IS NULL
          AND release_mbid IS NULL
          AND release_name IS NULL
          AND artist_mbids IS NULL
          AND artist_credit_name IS NULL
          AND recording_name IS NULL
        ) OR (
              match_type <> 'no_match'
          AND artist_credit_id IS NOT NULL
          AND recording_mbid IS NOT NULL
          AND release_mbid IS NOT NULL
          AND release_name IS NOT NULL
          AND artist_mbids IS NOT NULL
          AND artist_credit_name IS NOT NULL
          AND recording_name IS NOT NULL
        )
    );
COMMIT;
