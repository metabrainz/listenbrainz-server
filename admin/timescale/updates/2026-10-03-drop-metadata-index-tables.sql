-- Drop the metadata index tables after they have been moved to the listens DB. Only run this in a
-- separate cleanup once the new code has been running against the listens DB.
BEGIN;

DROP TABLE mapping.spotify_metadata_index;
DROP TABLE mapping.apple_metadata_index;
DROP TABLE mapping.soundcloud_metadata_index;

COMMIT;
