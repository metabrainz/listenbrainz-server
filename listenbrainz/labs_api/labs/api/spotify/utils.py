import re

import psycopg2

from unidecode import unidecode
from psycopg2.extras import execute_values
from listenbrainz import config


def perform_combined_lookup(column: str, lookups: list[tuple]):
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


def lookup_using_metadata(params):
    metadata = {}
    lookups = []
    for idx, item in enumerate(params):
        metadata[idx] = item
        combined_text_all = item["artist_name"] + item["release_name"] + item["track_name"]
        combined_lookup_all = unidecode(re.sub(r'[^\w]+', '', combined_text_all).lower())
        lookups.append((idx, combined_lookup_all))

    remaining_lookups = []
    index = perform_combined_lookup("combined_lookup_all", lookups)
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
        index = perform_combined_lookup("combined_lookup_without_album", remaining_lookups)
        print(index)
        for idx, spotify_id in index.items():
            metadata[idx]["spotify_track_id"] = spotify_id

    return list(metadata.values())

