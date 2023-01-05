import uuid

import psycopg2
from psycopg2.extras import execute_values
from datasethoster import Query
from flask import current_app
from werkzeug.exceptions import BadRequest

from listenbrainz.labs_api.labs.api.spotify.utils import lookup_using_metadata
from listenbrainz.db.recording import resolve_redirect_mbids, resolve_canonical_mbids


class SpotifyIdFromMBIDQuery(Query):
    """ Query to lookup spotify track ids using recording mbids. """

    def names(self):
        return "spotify-id-from-mbid", "Spotify Track ID Lookup using recording mbid"

    def inputs(self):
        return ['[recording_mbid]']

    def introduction(self):
        return """Given a recording mbid, lookup its metadata using canonical metadata
        tables and using that attempt to find a suitable match in Spotify."""

    def outputs(self):
        return ['recording_mbid', 'artist_name', 'release_name', 'track_name', 'spotify_track_ids']

    def fetch_metadata_from_mbids(self, curs, mbids):
        """ Retrieve metadata from canonical tables for given mbids. Note that all mbids should be canonical mbids
        otherwise metadata may not be found. """
        query = """
              WITH mbids(gid) AS (VALUES %s)
            SELECT recording_mbid::TEXT
                 , COALESCE(recording_name, '')
                 , COALESCE(artist_credit_name, '')
                 , COALESCE(release_name, '')
              FROM mapping.canonical_musicbrainz_data
        RIGHT JOIN mbids
                ON recording_mbid = gid::UUID
        """
        execute_values(curs, query, [(mbid,) for mbid in mbids], page_size=len(mbids))

        metadata = {}
        for row in curs.fetchall():
            metadata[row[0]] = {
                "track_name": row[1],
                "artist_name": row[2],
                "release_name": row[3]
            }

        return metadata

    def fetch(self, params, offset=-1, count=-1):
        mbids = []
        for param in params:
            try:
                uuid.UUID(param["[recording_mbid]"])
            except (ValueError, TypeError):
                raise BadRequest(f"Invalid recording mbid: {param['[recording_mbid]']}")
            mbids.append(param["[recording_mbid]"])

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn, conn.cursor() as curs:
            redirected_mbids, redirect_index, _ = resolve_redirect_mbids(curs, "recording", mbids)

        with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as conn, conn.cursor() as curs:
            canonical_mbids, canonical_index, _ = resolve_canonical_mbids(curs, redirected_mbids)
            metadata = self.fetch_metadata_from_mbids(curs, canonical_mbids)

        ordered_metadata = []
        for mbid in mbids:
            # check whether mbid was redirected before looking up metadata
            redirected_mbid = redirect_index.get(mbid, mbid)
            canonical_mbid = canonical_index.get(redirected_mbid, redirected_mbid)

            mbid_metadata = metadata[canonical_mbid]
            # regardless of whether we redirected the mbid, add the original mbid in the response returned to user
            mbid_metadata["recording_mbid"] = mbid
            ordered_metadata.append(mbid_metadata)

        return lookup_using_metadata(ordered_metadata)
