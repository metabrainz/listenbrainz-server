import psycopg2.extras
from datasethoster import Query
from flask import current_app

from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects


class RecordingFromRecordingMBIDQuery(Query):
    """ Look up a musicbrainz data for a list of recordings, based on MBID. """

    def names(self):
        return "recording-mbid-lookup", "MusicBrainz Recording by MBID Lookup"

    def inputs(self):
        return ['[recording_mbid]']

    def introduction(self):
        return """Look up recording and artist information given a recording MBID"""

    def outputs(self):
        return ['recording_mbid', 'recording_name', 'length', 'artist_credit_id', 'artist_credit_name',
                '[artist_credit_mbids]', 'canonical_recording_mbid', 'original_recording_mbid']

    def fetch(self, params, offset=-1, count=-1):
        if not current_app.config["MB_DATABASE_URI"]:
            return []

        mbids = [p['[recording_mbid]'] for p in params]
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as ts_curs:
            output = load_recordings_from_mbids_with_redirects(mb_curs, ts_curs, mbids)

            for item in output:
                item.pop("caa_id", None)
                item.pop("caa_release_mbid", None)

        # Ideally offset and count should be handled by the postgres query itself, but the 1:1 relationship
        # of what the user requests and what we need to fetch is no longer true, so we can't easily use LIMIT/OFFSET.
        # We might be able to use a RIGHT JOIN to fix this, but for now I'm happy to leave this as it. We need to
        # revisit this when we get closer to pushing recommendation tools to production.
        if offset > 0 and count > 0:
            return output[offset:offset+count]

        if offset > 0 and count < 0:
            return output[offset:]

        if offset < 0 and count > 0:
            return output[:count]

        return output
