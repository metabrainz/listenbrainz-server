-- For empty installations only. For existing data, restore the schema dump as described
-- in 2026-10-03-move-messybrainz.md instead.
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

CREATE TABLE messybrainz.submissions_redirect (
    duplicate_msid UUID NOT NULL,
    original_msid UUID NOT NULL
);

-- messybrainz
CREATE UNIQUE INDEX messybrainz_gid_ndx ON messybrainz.submissions (gid);
-- can't use a single index here because some values in these columns are too large and exceed the max
-- index size allowed when used together.
CREATE INDEX messybrainz_recording_ndx ON messybrainz.submissions (lower(recording));
CREATE INDEX messybrainz_artist_credit_ndx ON messybrainz.submissions (lower(artist_credit));
CREATE INDEX messybrainz_release_ndx ON messybrainz.submissions (lower(release));
CREATE INDEX messybrainz_track_number_ndx ON messybrainz.submissions (lower(track_number));
CREATE INDEX messybrainz_duration_ndx ON messybrainz.submissions (duration);

CREATE UNIQUE INDEX messybrainz_redirect_gid_ndx ON messybrainz.submissions_redirect (duplicate_msid);

ALTER TABLE messybrainz.submissions_redirect
    ADD CONSTRAINT messybrainz_submissions_msid_foreign_key
    FOREIGN KEY (original_msid)
    REFERENCES messybrainz.submissions (gid)
    ON DELETE NO ACTION;
COMMIT;
