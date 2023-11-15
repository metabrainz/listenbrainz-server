begin;

CREATE TABLE messybrainz.submissions_unique (
    id              INTEGER GENERATED ALWAYS AS IDENTITY NOT NULL PRIMARY KEY,
    gid             UUID NOT NULL UNIQUE,
    recording       TEXT NOT NULL,
    artist_credit   TEXT NOT NULL,
    release         TEXT,
    track_number    TEXT,
    duration        INTEGER,
    submitted       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE messybrainz.submissions_redirect (
    duplicate_msid UUID NOT NULL UNIQUE,
    original_msid UUID NOT NULL REFERENCES messybrainz.submissions_unique (gid)
);

with gather_data as (
       select recording
            , artist_credit
            , release
            , track_number
            , duration
            , (array_agg(submitted order by submitted))[1] AS original_submitted
            , array_agg(gid order by submitted, gid) AS msids
         from messybrainz.submissions
     group by recording
            , artist_credit
            , release
            , track_number
            , duration
), copy_to_new_table as (
  insert into messybrainz.submissions_unique as msb (gid, recording, artist_credit, release, track_number, duration, submitted)
       select msids[1]
            , recording
            , artist_credit
            , release
            , track_number
            , duration
            , original_submitted
         from gather_data gd
  on conflict (gid)
   do nothing
) insert into messybrainz.submissions_redirect (duplicate_msid, original_msid)
       select duplicate_msid
            , msids[1]
         from gather_data ctnt
 join lateral unnest(msids[2:]) AS duplicate_msid
           on true
        where array_length(msids, 1) > 1
  on conflict (duplicate_msid)
   do nothing;

commit;
