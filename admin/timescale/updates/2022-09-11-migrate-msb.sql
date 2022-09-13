BEGIN;

CREATE SCHEMA messybrainz;

CREATE TABLE messybrainz.submissions (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL,
    gid             UUID NOT NULL,
    recording       TEXT NOT NULL,
    artist_credit   TEXT NOT NULL,
    release         TEXT,
    track_number    TEXT,
    duration        INTEGER,
    submitted       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX messybrainz_gid_ndx ON messybrainz.submissions (gid);
-- can't have a unique index here due to historical duplicates
CREATE INDEX messybrainz_data_ndx ON messybrainz.submissions (lower(recording), lower(artist_credit), lower(release), lower(track_number), duration);


COMMIT;