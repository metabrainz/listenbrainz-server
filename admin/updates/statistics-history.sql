BEGIN;

CREATE TABLE statistics (
    collected   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    name        TEXT NOT NULL,
    value       INTEGER NOT NULL
);

ALTER TABLE statistics ADD CONSTRAINT statistics_pkey PRIMARY KEY (name, collected);

INSERT INTO statistics (collected, name, value)
    WITH uniques AS (SELECT DISTINCT ON (mbid) lowlevel.* FROM lowlevel ORDER BY mbid, lossless DESC)
    SELECT DISTINCT date_trunc('hour', submitted) + interval '1 hour' AS collected, CASE WHEN lossless THEN 'lowlevel-lossless-unique' ELSE 'lowlevel-lossy-unique' END, count(*) OVER (PARTITION BY lossless ORDER BY date_trunc('hour', submitted) ASC)
      FROM uniques
     WHERE date_trunc('hour', submitted) != date_trunc('hour', now())
  ORDER BY date_trunc('hour', submitted) + interval '1 hour';

INSERT INTO statistics (collected, name, value)
    SELECT DISTINCT date_trunc('hour', submitted) + interval '1 hour' AS collected, CASE WHEN lossless THEN 'lowlevel-lossless' ELSE 'lowlevel-lossy' END, count(*) over (PARTITION BY lossless ORDER BY date_trunc('hour', submitted) asc)
      FROM lowlevel
     WHERE date_trunc('hour', submitted) != date_trunc('hour', now())
  ORDER BY date_trunc('hour', submitted) + interval '1 hour';

COMMIT;
