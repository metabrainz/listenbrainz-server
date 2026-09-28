BEGIN;

CREATE TABLE statistics_generation (
  stats_type    TEXT PRIMARY KEY,
  last_updated  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMIT;
