import psycopg2
from psycopg2.extras import execute_values
from datasethoster import Query

from listenbrainz import config
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

    def canonicalize_mbids(self, curs, mbids):
        query = """
              WITH mbids (gid) AS (VALUES %s)
            SELECT recording_mbid::TEXT AS old
                 , canonical_recording_mbid::TEXT AS new
              FROM mapping.canonical_recording_redirect
              JOIN mbids
                ON recording_mbid = gid::UUID
        """
        execute_values(curs, query, [(mbid,) for mbid in mbids], page_size=len(mbids))
        index = {}
        reverse_index = {}
        for row in curs.fetchall():
            index[row[0]] = row[1]
            reverse_index[row[1]] = row[0]

        canonical_mbids = []
        for mbid in mbids:
            if mbid in index:
                canonical_mbids.append(index[mbid])
            else:
                canonical_mbids.append(mbid)

        return canonical_mbids, index, reverse_index

    def fetch_metadata_from_mbids(self, original_mbids):
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
        with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as conn, conn.cursor() as curs:
            canonical_mbids, index, reverse_index = self.canonicalize_mbids(curs, original_mbids)

            execute_values(curs, query, [(mbid,) for mbid in canonical_mbids], page_size=len(canonical_mbids))

            metadata = {}
            for row in curs.fetchall():
                metadata[row[0]] = {
                    "track_name": row[1],
                    "artist_name": row[2],
                    "release_name": row[3]
                }

            ordered_metadata = []
            for mbid in original_mbids:
                if mbid in index:
                    redirect_mbid = index[mbid]
                    mbid_metadata = metadata[redirect_mbid]
                else:
                    mbid_metadata = metadata[mbid]

                mbid_metadata["recording_mbid"] = mbid
                ordered_metadata.append(mbid_metadata)
            return ordered_metadata

    def fetch(self, params, offset=-1, count=-1):
        mbids = []
        for param in params:
            # TODO: Validate mbids here
            mbids.append(param["[recording_mbid]"])

        metadata = self.fetch_metadata_from_mbids(mbids)
        return lookup_using_metadata(metadata)
