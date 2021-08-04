BEGIN;

-- When adding a column, timescale goes through and disables the autovacuum for each chunk
-- but it does this _after_ it takes an exclusive lock on the table.
-- By disabling it manually first we make the column add operation fast
alter table listen set (autovacuum_enabled = false);
-- Postgres 11+ can add a column with non-null + default without locking the table
-- https://dataegret.com/2018/03/waiting-for-postgresql-11-pain-free-add-column-with-non-null-defaults/
-- we use user_id=0 as a sentinel (no user exists with this id)
-- After the migrate script runs we shouldn't have any listens with a user_id of 0
alter table listen add column user_id integer not null default 0;

COMMIT;

-- index so that we can quickly see which listens have user_id of 0. We'll need it when selecting
-- on this field after we remove user_name, too.
-- It doesn't appear to affect bulk update speed too much with this index in place
-- CREATE INDEX will lock the whole table, which means that it'll be unavailable while the index
-- is building. Timescale doesn't support CREATE INDEX CONCURRENTLY. The best we can do is this
-- extension which opens a transaction and creates the index one chunk at a time.
-- This lets inserts and selects work on the table while it's running
-- This operation doesn't support being run inside a transaction.
create index user_id_listen on listen(user_id) WITH (timescaledb.transaction_per_chunk);

-- turn autovacuum back on
alter table listen set (autovacuum_enabled = true);
