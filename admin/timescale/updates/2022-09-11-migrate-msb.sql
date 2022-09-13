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
-- can't use a single index here because some values in these columns are too large and exceed the max
-- index size allowed when used together.
CREATE INDEX messybrainz_recording_ndx ON messybrainz.submissions (lower(recording));
CREATE INDEX messybrainz_artist_credit_ndx ON messybrainz.submissions (lower(artist_credit));
CREATE INDEX messybrainz_release_ndx ON messybrainz.submissions (lower(release));
CREATE INDEX messybrainz_track_number_ndx ON messybrainz.submissions (lower(track_number));
CREATE INDEX messybrainz_duration_ndx ON messybrainz.submissions (duration);


COMMIT;