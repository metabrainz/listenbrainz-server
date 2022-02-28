-- CREATE INDEX will lock the whole table, which means that it'll be unavailable while the index
-- is building. Timescale doesn't support CREATE INDEX CONCURRENTLY. The best we can do is this
-- extension which opens a transaction and creates the index one chunk at a time.
-- This lets inserts and selects work on the table while it's running
-- This operation doesn't support being run inside a transaction.
CREATE INDEX listened_at_user_id_ndx_listen ON listen (listened_at DESC, user_id) WITH (timescaledb.transaction_per_chunk);

-- unique index cannot be created using transaction_per_chunk
CREATE UNIQUE INDEX listened_at_track_name_user_id_ndx_listen ON listen (listened_at DESC, track_name, user_id);

-- the user_id was initially set to DEFAULT to 0 while a background process updated user ids
-- according to the user name now the process is complete so a default is no longer needed.
BEGIN;
ALTER TABLE listen ALTER COLUMN user_id DROP DEFAULT;
COMMIT;
