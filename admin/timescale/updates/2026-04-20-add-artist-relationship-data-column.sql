BEGIN;

ALTER TABLE mapping.mb_artist_metadata_cache 
ADD COLUMN IF NOT EXISTS artist_relationship_data JSONB NOT NULL DEFAULT '[]'::JSONB;

COMMIT;