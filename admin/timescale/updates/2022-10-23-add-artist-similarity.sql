BEGIN;

CREATE TABLE similarity.artist (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    metadata JSONB NOT NULL
);

CREATE UNIQUE INDEX similar_artists_uniq_idx ON similarity.artist (mbid0, mbid1);
-- reverse index is only needed for performance reasons
CREATE UNIQUE INDEX similar_artists_reverse_uniq_idx ON similarity.artist (mbid1, mbid0);
CREATE INDEX similar_artists_algorithm_idx ON similarity.artist USING gin (metadata);

COMMIT;
