CREATE TYPE data_dump_type_type AS ENUM ('incremental', 'full');

BEGIN;

ALTER TABLE data_dump ADD COLUMN dump_type data_dump_type_type;

COMMIT;
