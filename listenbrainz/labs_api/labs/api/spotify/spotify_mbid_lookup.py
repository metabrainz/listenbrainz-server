import uuid

import psycopg2
from psycopg2.extras import execute_values
from datasethoster import Query
from flask import current_app
from werkzeug.exceptions import BadRequest

from listenbrainz.labs_api.labs.api.spotify.utils import lookup_using_metadata


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
        return ['recording_mbid', 'artist_name', 'release_name', 'track_name', 'spotify_track_id']

    def resolve_redirect_mbids(self, mbids):
        """ Given a list of mbids, resolve redirects if any and return the list of new mbids and a dict of
        redirected mbids.
        """
        query = """
              WITH mbids (gid) AS (VALUES %s)
            SELECT rgr.gid::TEXT AS old
                 , r.gid::TEXT AS new
              FROM recording_gid_redirect rgr
              JOIN mbids m
                ON rgr.gid = m.gid::UUID
              JOIN recording r
                ON r.id = rgr.new_id
        """
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn, conn.cursor() as curs:
            execute_values(curs, query, [(mbid,) for mbid in mbids], page_size=len(mbids))
            index = {row[0]: row[1] for row in curs.fetchall()}

        redirected_mbids = []
        for mbid in mbids:
            # redirect the mbid to find the new recording if one exists otherwise use the original mbid itself
            redirected_mbids.append(index.get(mbid, mbid))

        return redirected_mbids, index

    def resolve_canonical_mbids(self, mbids):
        """ Check the list of mbids for canonical redirects and return list of canonical mbids.

        Args:
            mbids: list of mbids to check for canonical mbids

        Returns:
            tuple of (list of canonical mbids, dict of redirected mbids as key and the canonical mbid
            replacing it as value)
        """
        query = """
              WITH mbids (gid) AS (VALUES %s)
            SELECT recording_mbid::TEXT AS old
                 , canonical_recording_mbid::TEXT AS new
              FROM mapping.canonical_recording_redirect
              JOIN mbids
                ON recording_mbid = gid::UUID
        """
        with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as conn, conn.cursor() as curs:
            execute_values(curs, query, [(mbid,) for mbid in mbids], page_size=len(mbids))
            index = {row[0]: row[1] for row in curs.fetchall()}

        canonical_mbids = []
        for mbid in mbids:
            # get the canonical mbid redirect if one exists otherwise the original mbid is the canonical one itself
            canonical_mbids.append(index.get(mbid, mbid))

        return canonical_mbids, index

    def fetch_metadata_from_mbids(self, mbids):
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
        with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as conn, conn.cursor() as curs:
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

        redirected_mbids, redirect_index = self.resolve_redirect_mbids(mbids)
        canonical_mbids, canonical_index = self.resolve_canonical_mbids(redirected_mbids)

        metadata = self.fetch_metadata_from_mbids(canonical_mbids)

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
