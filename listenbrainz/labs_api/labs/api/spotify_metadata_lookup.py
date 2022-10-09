import re
import uuid

import psycopg2
from psycopg2.extras import execute_values
from datasethoster import Query
from unidecode import unidecode

from listenbrainz import config


class SpotifyIdFromMetadataQuery(Query):
    """ Query to lookup spotify track ids using artist name, release name and track name. """

    def names(self):
        return "spotify-id-from-metadata", "Spotify Track ID Lookup using metadata"

    def inputs(self):
        return ['[artist_name]', '[release_name]', '[track_name]']

    def introduction(self):
        return """Given the name of an artist, the name of a release and the name of a recording (track)
                  this query will attempt to find a suitable match in Spotify."""

    def outputs(self):
        return ['artist_name_arg', 'release_name_arg', 'track_name_arg', 'spotify_track_id']

    def perform_lookup(self, column, lookups):
        with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as conn, conn.cursor() as curs:
            query = f"""
                  WITH lookups (idx, value) AS (VALUES %s)
                SELECT idx, track_id
                  FROM lookups
                  JOIN mapping.spotify_metadata_index
                    ON {column} = value
            """
            execute_values(curs, query, lookups, page_size=len(lookups))
            result = curs.fetchall()
            return {row[0]: row[1] for row in result}

    def _canonicalize_mbids(self, curs, mbids):
        query = """
              WITH mbids (gid) AS (VALUES %s)
            SELECT recording_mbid::TEXT AS old
                 , canonical_recording_mbid::TEXT AS new
              FROM mapping.canonical_recording_redirect
              JOIN mbids
                ON recording_mbid = gid::UUID
        """
        execute_values(curs, query, mbids, page_size=len(mbids))
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
        fetch_metadata_query = """
              WITH mbids(gid) AS (VALUES %s)
            SELECT recording_mbid::TEXT
                 , COALESCE(recording_name, '')
                 , COALESCE(artist_credit_name, '')
                 , COALESCE(release_name, '')
              FROM mapping.canonical_musicbrainz_data
        RIGHT JOIN mbids
                ON recording_mbid = gid
        """
        with psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI) as conn, conn.cursor() as curs:
            canonical_mbids, index, reverse_index = self._canonicalize_mbids(curs, original_mbids)

            execute_values(curs, fetch_metadata_query, canonical_mbids, page_size=len(canonical_mbids))

            metadata = {}
            for row in curs.fetchall():
                if row[0] in reverse_index:
                    mbid = reverse_index[row[0]]
                else:
                    mbid = row[0]

                metadata[mbid] = {
                    "recording_mbid": mbid,
                    "track_name": row[1],
                    "artist_name": row[2],
                    "release_name": row[3]
                }

            ordered_metadata = []
            for mbid in original_mbids:
                ordered_metadata.append(metadata[mbid])
            return ordered_metadata

    def fetch_from_mbids(self, params, offset=-1, count=-1):
        mbids = []
        mbids_index = {}
        for idx, param in enumerate(params):
            mbids_index[idx] = param["[recording_mbid]"]
            mbids.append((param["[recording_mbid]"],))

        metadata = self.fetch_metadata_from_mbids(mbids)
        lookedup_metadata = self.fetch_from_metadata(metadata)
        return self.fetch_from_metadata(lookedup_metadata)

    def fetch_from_metadata(self, params):
        metadata = {}
        lookups = []
        for idx, item in enumerate(params):
            metadata[idx] = item
            combined_text_all = item["artist_name_arg"] + item["release_name_arg"] + item["track_name_arg"]
            combined_lookup_all = unidecode(re.sub(r'[^\w]+', '', combined_text_all).lower())
            lookups.append((idx, combined_lookup_all))

        remaining_lookups = []
        index = self.perform_lookup("combined_lookup_all", lookups)
        for idx, item in metadata.items():
            spotify_id = index.get(idx)
            if spotify_id:
                metadata[idx]["spotify_track_id"] = spotify_id
            else:
                metadata[idx]["spotify_track_id"] = None

                combined_text_without_album = item["artist_name"] + item["track_name"]
                combined_lookup_without_album = unidecode(re.sub(r'[^\w]+', '', combined_text_without_album).lower())
                remaining_lookups.append((idx, combined_lookup_without_album))

        if remaining_lookups:
            index = self.perform_lookup("combined_lookup_without_album", lookups)
            for idx, spotify_id in index.items():
                metadata[idx]["spotify_track_id"] = spotify_id

        return list(metadata.values())

    def fetch(self, params, offset=-1, count=-1):
        data = []
        for param in params:
            data.append({
                "artist_name": param.get("[artist_name]", ""),
                "release_name": param.get("[release_name]", ""),
                "track_name": param.get("[track_name]", "")
            })
        return self.fetch_from_metadata(data)
