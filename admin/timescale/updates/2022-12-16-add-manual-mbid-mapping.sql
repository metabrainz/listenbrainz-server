BEGIN;

CREATE TABLE mbid_manual_mapping(
    id             INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    recording_msid UUID NOT NULL,
    recording_mbid UUID NOT NULL,
    user_id        INTEGER NOT NULL,
    created        TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX recording_msid_user_id_mbid_manual_mapping_idx ON mbid_manual_mapping(recording_msid, user_id);

COMMIT;