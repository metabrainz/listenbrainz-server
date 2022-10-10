import re

import psycopg2

from flask import current_app
from unidecode import unidecode
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier


def detune(artist_name: str):
    phrases = [" ft ", " feat ", " ft. ", " feat. "]
    for phrase in phrases:
        artist_name = artist_name.replace(phrase, " ")
    return artist_name


def perform_combined_lookup(column: str, lookups: list[tuple]):
    query = SQL("""
          WITH lookups (idx, value) AS (VALUES %s)
        SELECT DISTINCT ON ({column})
               idx, track_id
          FROM lookups
          JOIN mapping.spotify_metadata_index
            ON {column} = value
      ORDER BY {column}, score DESC
    """).format(column=Identifier(column))

    with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as conn, conn.cursor() as curs:
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

    remaining_items = {}
    index = perform_combined_lookup("combined_lookup_all", lookups)
    for idx, item in metadata.items():
        spotify_id = index.get(idx)
        if spotify_id:
            metadata[idx]["spotify_track_id"] = spotify_id
        else:
            metadata[idx]["spotify_track_id"] = None
            remaining_items[idx] = item

    if remaining_items:
        remaining_lookups = []
        for idx, item in remaining_items.items():
            combined_text_all_detuned = detune(item["artist_name"]) + item["release_name"] + item["track_name"]
            combined_lookup_all_detuned = unidecode(re.sub(r'[^\w]+', '', combined_text_all_detuned).lower())
            remaining_lookups.append((idx, combined_lookup_all_detuned))

        index = perform_combined_lookup("combined_lookup_all", remaining_lookups)
        for idx, spotify_id in index.items():
            metadata[idx]["spotify_track_id"] = spotify_id
            remaining_items.pop(idx, None)

    if remaining_items:
        remaining_lookups = []
        for idx, item in remaining_items.items():
            combined_text_without_album = item["artist_name"] + item["track_name"]
            combined_lookup_without_album = unidecode(re.sub(r'[^\w]+', '', combined_text_without_album).lower())
            remaining_lookups.append((idx, combined_lookup_without_album))

        index = perform_combined_lookup("combined_lookup_without_album", remaining_lookups)
        for idx, spotify_id in index.items():
            metadata[idx]["spotify_track_id"] = spotify_id
            remaining_items.pop(idx, None)

    if remaining_items:
        remaining_lookups = []
        for idx, item in remaining_items.items():
            combined_text_without_album_detuned = detune(item["artist_name"]) + item["track_name"]
            combined_lookup_without_album_detuned = unidecode(re.sub(r'[^\w]+', '', combined_text_without_album_detuned).lower())
            remaining_lookups.append((idx, combined_lookup_without_album_detuned))

        index = perform_combined_lookup("combined_lookup_without_album", remaining_lookups)
        for idx, spotify_id in index.items():
            metadata[idx]["spotify_track_id"] = spotify_id
            remaining_items.pop(idx, None)

    return list(metadata.values())

