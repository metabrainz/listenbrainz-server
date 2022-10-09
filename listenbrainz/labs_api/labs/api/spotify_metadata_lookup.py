import re

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

    def fetch(self, params, offset=-1, count=-1):
        metadata = {}
        lookups = []
        for idx, param in enumerate(params):
            artist_name_arg = param.get("[artist_name]", "")
            release_name_arg = param.get("[release_name]", "")
            track_name_arg = param.get("[track_name]", "")
            metadata[idx] = {
                "artist_name_arg": artist_name_arg,
                "release_name_arg": release_name_arg,
                "track_name_arg": track_name_arg
            }

            combined_text_all = artist_name_arg + release_name_arg + track_name_arg
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

                combined_text_without_album = item["artist_name_arg"] + item["track_name_arg"]
                combined_lookup_without_album = unidecode(re.sub(r'[^\w]+', '', combined_text_without_album).lower())
                remaining_lookups.append((idx, combined_lookup_without_album))

        if remaining_lookups:
            index = self.perform_lookup("combined_lookup_without_album", lookups)
            for idx, spotify_id in index.items():
                metadata[idx]["spotify_track_id"] = spotify_id

        return list(metadata.values())
