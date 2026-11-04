-- Drop the mapping tables after they have been moved to the listens DB. Only run this in a separate
-- cleanup once the new code has been running against the listens DB and a backup of the listens DB
-- mapping schema has been verified. See admin/listens/updates/2026-10-02-move-mapping-tables.md.
BEGIN;

DROP MATERIALIZED VIEW mbid_manual_mapping_top;
DROP TABLE mbid_manual_mapping;
DROP TABLE mbid_mapping;
DROP TABLE mbid_mapping_metadata;
DROP TABLE background_worker_state;
DROP TYPE mbid_mapping_match_type_enum;
DROP SCHEMA mapping CASCADE;

COMMIT;
