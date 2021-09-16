CREATE TYPE stats_range_type AS ENUM ('week', 'month', 'year', 'all_time');

CREATE TYPE user_stats_type AS ENUM('artists', 'releases', 'recordings', 'daily_activity', 'listening_activity', 'artist_map');

BEGIN;

CREATE TABLE statistics.user_new (
    id                      SERIAL, -- PK
    user_id                 INTEGER NOT NULL, -- FK to "user".id
    stats_type              user_stats_type,
    stats_range             stats_range_type,
    data                    JSONB,
    count                   INTEGER,
    -- we use int timestamps when serializing data in spark, we return the same from the api
    -- using timestamp with time zone here just complicates stuff. we'll need to add
    -- datetime/timestamp conversions in code at multiple places and we never seem to use this
    -- value anyways in LB backend atm.
    from_ts                 BIGINT,
    to_ts                   BIGINT,
    last_updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

ALTER TABLE statistics.user_new ADD CONSTRAINT stats_user_new_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX user_type_range_ndx_stats ON statistics.user_new (user_id, stats_type, stats_range);
CREATE INDEX user_id_ndx__user_stats_new ON statistics.user_new (user_id);

ALTER TABLE statistics.user_new
    ADD CONSTRAINT user_stats_new_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

COMMIT;
