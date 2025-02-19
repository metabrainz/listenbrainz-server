CREATE TYPE listen_delete_metadata_status_enum AS ENUM ('pending', 'invalid', 'complete');

BEGIN;

ALTER TABLE listen_delete_metadata ADD COLUMN status listen_delete_metadata_status_enum NOT NULL DEFAULT 'pending';
ALTER TABLE listen_delete_metadata
    ADD CONSTRAINT listen_delete_metadata_status_created_constraint
    CHECK ( status = 'invalid' OR status = 'pending' OR (status = 'complete' AND listen_created IS NOT NULL) );

UPDATE listen_delete_metadata SET status = (CASE WHEN deleted IS TRUE THEN 'complete' ELSE 'pending' END)::listen_delete_metadata_status_enum;

ALTER TABLE listen_delete_metadata DROP CONSTRAINT listen_delete_metadata_deleted_created_constraint;
ALTER TABLE listen_delete_metadata DROP COLUMN deleted;

COMMIT;
