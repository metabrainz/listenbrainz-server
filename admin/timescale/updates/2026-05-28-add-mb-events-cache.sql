BEGIN;

CREATE TABLE mapping.mb_event_cache (
    dirty                BOOLEAN DEFAULT FALSE,
    last_updated         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    event_mbid           UUID NOT NULL,
    event_id             INTEGER NOT NULL,
    event_name           TEXT NOT NULL,

    begin_date_year      SMALLINT,
    begin_date_month     SMALLINT,
    begin_date_day       SMALLINT,
    end_date_year        SMALLINT,
    end_date_month       SMALLINT,
    end_date_day         SMALLINT,
    event_time           TIMESTAMPTZ,
    cancelled            BOOLEAN NOT NULL DEFAULT FALSE,
    ended                BOOLEAN NOT NULL DEFAULT FALSE,

    event_type_gid       UUID,
    event_art_presence   TEXT NOT NULL DEFAULT 'absent',

    place_mbid           UUID,
    place_name           TEXT,
    area_mbid            UUID,

    rating               SMALLINT,
    rating_count         INTEGER,

    event_data           JSONB NOT NULL
);

ALTER TABLE mapping.mb_event_cache
    ADD CONSTRAINT mb_event_cache_pkey PRIMARY KEY (event_mbid);

CREATE UNIQUE INDEX mb_event_cache_idx_event_id ON mapping.mb_event_cache (event_id);
CREATE INDEX mb_event_cache_idx_date ON mapping.mb_event_cache (begin_date_year, begin_date_month, begin_date_day);
CREATE INDEX mb_event_cache_idx_dirty ON mapping.mb_event_cache (dirty);

CREATE TABLE mapping.mb_event_artist_cache (
    event_mbid           UUID NOT NULL,
    event_id             INTEGER NOT NULL,
    artist_mbid          UUID NOT NULL,
    artist_id            INTEGER NOT NULL,

    link_id              INTEGER NOT NULL,
    link_order           INTEGER NOT NULL DEFAULT 0,
    link_type_gid        UUID NOT NULL,  
    link_type_name       TEXT NOT NULL,

    relationship_data    JSONB NOT NULL,
    last_updated         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE mapping.mb_event_artist_cache
    ADD CONSTRAINT mb_event_artist_cache_pkey
    PRIMARY KEY (event_id, artist_id, link_id, link_order);

CREATE INDEX mb_event_artist_cache_idx_artist_id_event_id ON mapping.mb_event_artist_cache (artist_id, event_id);
CREATE INDEX mb_event_artist_cache_idx_artist_mbid ON mapping.mb_event_artist_cache (artist_mbid);
CREATE INDEX mb_event_artist_cache_idx_event_id ON mapping.mb_event_artist_cache (event_id);
CREATE INDEX mb_event_artist_cache_idx_link_type_gid ON mapping.mb_event_artist_cache (link_type_gid);

COMMIT;
