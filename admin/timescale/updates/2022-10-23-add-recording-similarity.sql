BEGIN;

CREATE SCHEMA similarity;

CREATE TABLE similarity.recording (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    metadata JSONB NOT NULL
);

CREATE UNIQUE INDEX similar_recordings_uniq_idx ON similarity.recording (mbid0, mbid1);
-- reverse index is only needed for performance reasons
CREATE UNIQUE INDEX similar_recordings_reverse_uniq_idx ON similarity.recording (mbid1, mbid0);
CREATE INDEX similar_recordings_algorithm_idx ON similarity.recording USING gin (metadata);

COMMIT;
