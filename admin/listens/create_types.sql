BEGIN;

CREATE TYPE listen_delete_metadata_status_enum AS ENUM ('pending', 'invalid', 'complete');
CREATE TYPE mapping.mbid_mapping_match_type_enum AS ENUM('no_match', 'low_quality', 'med_quality', 'high_quality', 'exact_match');

COMMIT;
