BEGIN;

ALTER TABLE listen_delete_metadata ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE listen_delete_metadata ADD COLUMN listen_created TIMESTAMP WITH TIME ZONE;
ALTER TABLE listen_delete_metadata
    ADD CONSTRAINT listen_delete_metadata_deleted_created_constraint
    CHECK ( deleted IS FALSE OR (deleted IS TRUE AND listen_created IS NOT NULL) );

COMMIT;
