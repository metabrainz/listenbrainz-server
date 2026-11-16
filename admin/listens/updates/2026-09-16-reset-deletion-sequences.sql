-- Run in the listens DB after importing deletion records with their existing IDs.
-- These are new destination sequences, independent of the Timescale sequences.
-- Advance each to the largest imported ID so the next insert cannot reuse an ID.
-- For an empty table, the next generated ID remains 1. Fresh schema setup does
-- not need this step because it creates empty tables with initialized sequences.
-- Pause deletion writers during the import and this reset.
BEGIN;

SELECT setval(pg_get_serial_sequence('listen_delete_metadata', 'id'),
              COALESCE(max(id), 1), max(id) IS NOT NULL)
  FROM listen_delete_metadata;
SELECT setval(pg_get_serial_sequence('deleted_user_listen_history', 'id'),
              COALESCE(max(id), 1), max(id) IS NOT NULL)
  FROM deleted_user_listen_history;

COMMIT;
