BEGIN;

CREATE TYPE listen_delete_metadata_status_enum AS ENUM ('pending', 'invalid', 'complete');

COMMIT;
