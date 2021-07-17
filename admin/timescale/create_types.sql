BEGIN;

CREATE TYPE mbid_mapping_match_type_enum AS ENUM('no_match', 'low_quality', 'med_quality', 'high_quality', 'exact_match');

COMMIT;
