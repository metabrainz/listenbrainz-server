-- CREATE INDEX will lock the whole table, which means that it'll be unavailable while the index
-- is building. Timescale doesn't support CREATE INDEX CONCURRENTLY. The best we can do is this
-- extension which opens a transaction and creates the index one chunk at a time.
-- This lets inserts and selects work on the table while it's running
-- This operation doesn't support being run inside a transaction.
CREATE INDEX listened_at_user_id_ndx_listen ON listen (listened_at DESC, user_id) WITH (timescaledb.transaction_per_chunk);
CREATE UNIQUE INDEX listened_at_track_name_user_id_ndx_listen ON listen (listened_at DESC, track_name, user_id) WITH (timescaledb.transaction_per_chunk);
