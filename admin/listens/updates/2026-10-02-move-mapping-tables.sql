-- Create the mapping tables that lived in Timescale's public schema in the mapping schema of the
-- listens DB, without indexes so that the data can be copied in quickly. Then copy the data and run
-- 2026-10-02-move-mapping-tables-indexes.sql.
BEGIN;

CREATE TYPE mapping.mbid_mapping_match_type_enum AS ENUM('no_match', 'low_quality', 'med_quality', 'high_quality', 'exact_match');

CREATE TABLE mapping.mbid_manual_mapping (
    id             INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    recording_msid UUID NOT NULL,
    recording_mbid UUID NOT NULL,
    user_id        INTEGER NOT NULL,
    created        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE mapping.mbid_mapping (
        recording_msid      uuid not null,
        recording_mbid      uuid, -- FK mapping.mbid_mapping_metadata.recording_mbid
        match_type          mapping.mbid_mapping_match_type_enum NOT NULL,
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        check_again         TIMESTAMP WITH TIME ZONE
);

CREATE TABLE mapping.mbid_mapping_metadata (
        artist_credit_id    INT NOT NULL,
        recording_mbid      UUID NOT NULL,
        release_mbid        UUID NOT NULL,
        release_name        TEXT NOT NULL,
        artist_mbids        UUID[] NOT NULL,
        artist_credit_name  TEXT NOT NULL,
        recording_name      TEXT NOT NULL,
        last_updated        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE TABLE mapping.background_worker_state (
    key     TEXT NOT NULL,
    value   TEXT
);

COMMENT ON TABLE mapping.background_worker_state IS 'This table is used by the mbid mapping cron jobs to store the last update timestamps of the metadata caches.';

COMMIT;
