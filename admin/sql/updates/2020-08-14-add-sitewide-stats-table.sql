BEGIN;

CREATE TABLE statistics.sitewide (
    artist                  JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

COMMIT;
