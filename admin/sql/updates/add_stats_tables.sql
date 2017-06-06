BEGIN;

-- Create new schema
CREATE SCHEMA statistics;

-- Create new tables
CREATE TABLE statistics.user (
    user_id                 INTEGER NOT NULL, -- PK and FK to "user".id
    artists                 JSONB,
    releases                JSONB,
    recordings              JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE
);
ALTER TABLE statistics.user ADD CONSTRAINT user_stats_user_id_uniq UNIQUE (user_id);

CREATE TABLE statistics.artist (
    msid                    UUID NOT NULL, -- PK
    name                    VARCHAR,
    releases                JSONB,
    recordings              JSONB,
    users                   JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE
);
ALTER TABLE statistics.artist ADD CONSTRAINT artist_stats_msid_uniq UNIQUE (msid);

CREATE TABLE statistics.release (
    msid                    UUID NOT NULL, -- PK
    name                    VARCHAR,
    recordings              JSONB,
    users                   JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE
);
ALTER TABLE statistics.release ADD CONSTRAINT release_stats_msid_uniq UNIQUE (msid);

CREATE TABLE statistics.recording (
    msid                    UUID NOT NULL, -- PK
    name                    VARCHAR,
    users_all_time          JSONB,
    listen_count            JSONB,
    last_updated            TIMESTAMP WITH TIME ZONE

);
ALTER TABLE statistics.recording ADD CONSTRAINT recording_stats_msid_uniq UNIQUE (msid);

-- Create primary keys
ALTER TABLE statistics.user ADD CONSTRAINT stats_user_pkey PRIMARY KEY (user_id);
ALTER TABLE statistics.artist ADD CONSTRAINT stats_artist_pkey PRIMARY KEY (msid);
ALTER TABLE statistics.release ADD CONSTRAINT stats_release_pkey PRIMARY KEY (msid);
ALTER TABLE statistics.recording ADD CONSTRAINT stats_recording_pkey PRIMARY KEY (msid);

-- Create foreign key
ALTER TABLE statistics.user ADD CONSTRAINT user_stats_user_id_foreign_key FOREIGN KEY (user_id) REFERENCES "user" (id);

COMMIT;
