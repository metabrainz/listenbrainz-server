-- Add the keys, constraints and indexes of the mapping tables copied from Timescale's public schema,
-- after their data has been copied in. See 2026-10-02-move-mapping-tables.md.
BEGIN;

ALTER TABLE mapping.mbid_mapping_metadata ADD CONSTRAINT mbid_mapping_metadata_pkey PRIMARY KEY (recording_mbid);
ALTER TABLE mapping.background_worker_state ADD CONSTRAINT background_worker_state_pkey PRIMARY KEY (key);

ALTER TABLE mapping.mbid_mapping_metadata
    ADD CONSTRAINT mbid_mapping_metadata_artist_mbids_check
    CHECK ( array_ndims(artist_mbids) = 1 );

ALTER TABLE mapping.mbid_mapping
    ADD CONSTRAINT mbid_mapping_fields_null_check
    CHECK (
        (
              match_type = 'no_match'
          AND recording_mbid IS NULL
        ) OR (
              match_type <> 'no_match'
          AND recording_mbid IS NOT NULL
        )
    );

CREATE UNIQUE INDEX recording_msid_user_id_mbid_manual_mapping_idx ON mapping.mbid_manual_mapping(recording_msid, user_id);
CREATE UNIQUE INDEX recording_mbid_ndx_mbid_mapping_metadata ON mapping.mbid_mapping_metadata (recording_mbid);

CREATE UNIQUE INDEX recording_msid_ndx_mbid_mapping ON mapping.mbid_mapping (recording_msid);
CREATE INDEX recording_mbid_ndx_mbid_mapping ON mapping.mbid_mapping (recording_mbid);
CREATE INDEX match_type_ndx_mbid_mapping ON mapping.mbid_mapping (match_type);
CREATE INDEX last_updated_ndx_mbid_mapping ON mapping.mbid_mapping (last_updated);

-- the copied rows keep their ids, continue the identity after them
SELECT setval(
    pg_get_serial_sequence('mapping.mbid_manual_mapping', 'id'),
    COALESCE((SELECT max(id) FROM mapping.mbid_manual_mapping), 1),
    (SELECT count(*) > 0 FROM mapping.mbid_manual_mapping)
);

CREATE MATERIALIZED VIEW mapping.mbid_manual_mapping_top AS (
    SELECT DISTINCT ON (recording_msid)
           recording_msid
         , recording_mbid
      FROM mapping.mbid_manual_mapping
  GROUP BY recording_msid
         , recording_mbid
    HAVING count(DISTINCT user_id) >= 3
  ORDER BY recording_msid
         , count(*) DESC
         , max(created) DESC
);

CREATE INDEX mbid_manual_mapping_top_idx ON mapping.mbid_manual_mapping_top (recording_msid) INCLUDE (recording_mbid);

COMMIT;
