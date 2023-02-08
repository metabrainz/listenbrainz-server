BEGIN;

CREATE TABLE similarity.artist_credit_mbids (
    mbid0 UUID NOT NULL,
    mbid1 UUID NOT NULL,
    metadata JSONB NOT NULL
);

CREATE UNIQUE INDEX similar_artists_uniq_idx ON similarity.artist_credit_mbids (mbid0, mbid1);
-- reverse index is only needed for performance reasons
CREATE UNIQUE INDEX similar_artist_credit_mbids_reverse_uniq_idx ON similarity.artist_credit_mbids (mbid1, mbid0);
CREATE INDEX similar_artist_credit_mbids_algorithm_idx ON similarity.artist_credit_mbids USING gin (metadata);

COMMIT;
