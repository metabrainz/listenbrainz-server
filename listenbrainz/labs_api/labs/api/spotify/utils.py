import re
from enum import Enum

import psycopg2

from flask import current_app
from unidecode import unidecode
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier


class LookupType(Enum):
    ALL = "combined_lookup_all"
    WITHOUT_ALBUM = "combined_lookup_without_album"


def detune(artist_name: str) -> str:
    """ Remove commonly used join phrases from artist name """
    phrases = [" ft ", " feat ", " ft. ", " feat. "]
    for phrase in phrases:
        artist_name = artist_name.replace(phrase, " ")
    return artist_name


def query_combined_lookup(column: LookupType, lookups: list[tuple]):
    """ Lookup track ids for the given lookups in the metadata index using the specified lookup type"""
    query = SQL("""
          WITH lookups (idx, value) AS (VALUES %s)
        SELECT DISTINCT ON ({column})
               idx, array_agg(track_id ORDER BY score DESC) AS spotify_track_ids
          FROM lookups
          JOIN mapping.spotify_metadata_index
            ON {column} = value
      GROUP BY {column}, idx      
    """).format(column=Identifier(column.value))

    with psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as conn, conn.cursor() as curs:
        execute_values(curs, query, lookups, page_size=len(lookups))
        result = curs.fetchall()
        return {row[0]: row[1] for row in result}


def perform_lookup(column, metadata, generate_lookup):
    """ Given the lookup type and a function to generate to the lookup text, query database for spotify track ids """
    if not metadata:
        return metadata, {}

    lookups = []
    for idx, item in metadata.items():
        text = generate_lookup(item)
        lookup = unidecode(re.sub(r'[^\w]+', '', text).lower())
        lookups.append((idx, lookup))

    index = query_combined_lookup(column, lookups)

    remaining_items = {}
    for idx, item in metadata.items():
        spotify_ids = index.get(idx)
        if spotify_ids:
            metadata[idx]["spotify_track_ids"] = spotify_ids
        else:
            remaining_items[idx] = item

    return metadata, remaining_items


def combined_all(item) -> str:
    """ A lookup using original artist, release and track names """
    return item["artist_name"] + item["release_name"] + item["track_name"]


def combined_all_detuned(item) -> str:
    """ A lookup using detuned artist name and original release and track names """
    return detune(item["artist_name"]) + item["release_name"] + item["track_name"]


def combined_without_album(item) -> str:
    """ A lookup using artist name and track name but no release name """
    return item["artist_name"] + item["track_name"]


def combined_without_album_detuned(item) -> str:
    """ A lookup using detuned artist name, original track name but no release name """
    return detune(item["artist_name"]) + item["track_name"]


def lookup_using_metadata(params: list[dict]):
    """ Given a list of dicts each having artist name, release name and track name, attempt to find spotify track
    id for each. """
    metadata = {}
    for idx, item in enumerate(params):
        metadata[idx] = item

    # first attempt matching on artist, track and release followed by trying various detunings for unmatched recordings
    _, remaining_items = perform_lookup(LookupType.ALL, metadata, combined_all)
    _, remaining_items = perform_lookup(LookupType.ALL, remaining_items, combined_all_detuned)
    _, remaining_items = perform_lookup(LookupType.WITHOUT_ALBUM, remaining_items, combined_without_album)
    _, remaining_items = perform_lookup(LookupType.WITHOUT_ALBUM, remaining_items, combined_without_album_detuned)

    # to the still unmatched recordings, add null value so that each item has in the response has spotify_track_id key
    for item in remaining_items.values():
        item["spotify_track_ids"] = []

    return list(metadata.values())

