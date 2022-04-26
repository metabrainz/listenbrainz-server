BEGIN;

CREATE TABLE statistics.recording_discovery (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    user_id                 INTEGER NOT NULL,
    recording_mbid          UUID NOT NULL,
    first_listened_at       TIMESTAMP WITH TIME ZONE NOT NULL,
    latest_listened_at      TIMESTAMP WITH TIME ZONE NOT NULL
);

ALTER TABLE statistics.recording_discovery ADD CONSTRAINT stats_recording_discovery_pkey PRIMARY KEY (id);

ALTER TABLE statistics.recording_discovery
    ADD CONSTRAINT user_stats_recording_discovery_user_id_foreign_key
    FOREIGN KEY (user_id)
    REFERENCES "user" (id)
    ON DELETE CASCADE;

CREATE UNIQUE INDEX user_id_recording_mbid_ndx_recording_discovery ON statistics.recording_discovery (user_id, recording_mbid) INCLUDE (latest_listened_at);

COMMIT;
