BEGIN;

CREATE TABLE statistics.sitewide (
    id                      SERIAL, --pk
    stats_range             TEXT,
    artist                  JSONB,
    release                 JSONB,
    recording               JSONB,
    listening_activity      JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE statistics.sitewide ADD CONSTRAINT stats_range_uniq UNIQUE (stats_range);

COMMIT;
