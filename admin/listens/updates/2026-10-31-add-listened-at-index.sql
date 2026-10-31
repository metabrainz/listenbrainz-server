-- Index the listens DB listen table on listened_at, for full listen dumps and the mbid mapping
-- writer's legacy listens loader, which select listens by listened_at for all users. Deploy the code
-- that reads listens for these from the listens DB only after this script has finished.
--
-- Run with psql: it uses \gexec to build each partition's index concurrently, so that ingestion is
-- not blocked, then attaches them to the index on the parent, which becomes valid once all are
-- attached. Rerunning it after a failure skips the partition indexes that already exist, but drop
-- any of them left INVALID by the failure first.

CREATE INDEX IF NOT EXISTS listened_at_ndx_listen ON ONLY listen (listened_at);

SELECT format('CREATE INDEX CONCURRENTLY IF NOT EXISTS %I ON %I (listened_at)', c.relname || '_listened_at_idx', c.relname)
  FROM pg_inherits i
  JOIN pg_class c ON c.oid = i.inhrelid
 WHERE i.inhparent = 'listen'::regclass
 ORDER BY c.relname
\gexec

SELECT format('ALTER INDEX listened_at_ndx_listen ATTACH PARTITION %I', c.relname || '_listened_at_idx')
  FROM pg_inherits i
  JOIN pg_class c ON c.oid = i.inhrelid
 WHERE i.inhparent = 'listen'::regclass
   AND NOT EXISTS (
        SELECT 1
          FROM pg_inherits ii
         WHERE ii.inhparent = 'listened_at_ndx_listen'::regclass
           AND ii.inhrelid = (c.relname || '_listened_at_idx')::regclass
       )
 ORDER BY c.relname
\gexec
