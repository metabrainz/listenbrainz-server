begin;

insert into messybrainz.submissions_unique (gid, recording, artist_credit, release, track_number, duration, submitted)
     select gid
          , recording
          , artist_credit
          , release
          , track_number
          , duration
          , submitted
       from messybrainz.submissions
      where submitted > make_date(2023, 11, 15)
on conflict (gid)
 do nothing;

-- run query from first deduplicate script here with appropriate timestamp added

alter table messybrainz.submissions rename to submissions_old;
alter table messybrainz.submissions_unique rename to submissions;

CREATE INDEX messybrainz_submissions_recording_ndx ON messybrainz.submissions (lower(recording));
CREATE INDEX messybrainz_submissions_artist_credit_ndx ON messybrainz.submissions (lower(artist_credit));
CREATE INDEX messybrainz_submissions_release_ndx ON messybrainz.submissions (lower(release));
CREATE INDEX messybrainz_submissions_track_number_ndx ON messybrainz.submissions (lower(track_number));
CREATE INDEX messybrainz_submissions_duration_ndx ON messybrainz.submissions (duration);

commit;
