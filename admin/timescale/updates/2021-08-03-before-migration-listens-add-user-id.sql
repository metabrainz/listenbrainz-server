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

-- turn autovacuum back on
alter table listen set (autovacuum_enabled = true);
COMMIT;
