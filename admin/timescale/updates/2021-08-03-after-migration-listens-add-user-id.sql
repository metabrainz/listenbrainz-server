-- index so that we can quickly see which listens have user_id of 0. We'll need it when selecting
-- on this field after we remove user_name, too.
-- It doesn't appear to affect bulk update speed too much with this index in place
-- CREATE INDEX will lock the whole table, which means that it'll be unavailable while the index
-- is building. Timescale doesn't support CREATE INDEX CONCURRENTLY. The best we can do is this
-- extension which opens a transaction and creates the index one chunk at a time.
-- This lets inserts and selects work on the table while it's running
-- This operation doesn't support being run inside a transaction.
create index user_id_listen on listen(user_id) WITH (timescaledb.transaction_per_chunk);
