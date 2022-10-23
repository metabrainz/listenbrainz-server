BEGIN;

CREATE SCHEMA similarity;

CREATE TABLE similarity.recording (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    metadata JSONB NOT NULL

    CONSTRAINT alphabetical_uuids CHECK (mbid0 <= mbid1)
);

CREATE UNIQUE INDEX similar_recordings_uniq_idx ON similarity.recording (mbid0, mbid1);
CREATE INDEX similar_recordings_algorithm_idx ON similarity.recording USING gin (metadata);

COMMIT;
