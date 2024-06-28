import re
from enum import Enum

import psycopg2

from flask import current_app
from unidecode import unidecode
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier, Literal

from listenbrainz.labs_api.labs.api.spotify import SpotifyIdFromMBIDOutput
from listenbrainz.labs_api.labs.api.apple import AppleMusicIdFromMBIDOutput


class LookupType(Enum):
    ALL = "combined_lookup_all"
    WITHOUT_ALBUM = "combined_lookup_without_album"


def detune(artist_name: str) -> str:
    """ Remove commonly used join phrases from artist name """
    phrases = [" ft ", " feat ", " ft. ", " feat. "]
    for phrase in phrases:
        artist_name = artist_name.replace(phrase, " ")
    return artist_name


def query_combined_lookup(column: LookupType, lookups: list[tuple], service):
    """ Lookup track ids for the given lookups in the metadata index using the specified lookup type"""
    if service == 'spotify':
        table = 'mapping.spotify_metadata_index'
        track_ids = 'spotify_track_ids'
    elif service == 'apple_music':
        table = 'mapping.apple_metadata_index'
        track_ids = 'apple_music_track_ids'
    else:
        raise ValueError("Service must be either 'spotify' or 'apple_music'")

    query = SQL("""
          WITH lookups (idx, value) AS (VALUES %s)
        SELECT DISTINCT ON ({column})
               idx, array_agg(track_id ORDER BY score DESC) AS {track_ids}
          FROM lookups
          JOIN {table}
            ON {column} = value
      GROUP BY {column}, idx      
    """).format(column=Identifier(column.value), table=SQL(table), track_ids=Identifier(track_ids))

    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn, conn.cursor() as curs:
        execute_values(curs, query, lookups, page_size=len(lookups))
        result = curs.fetchall()
        return {row[0]: row[1] for row in result}


def perform_lookup(column, metadata, generate_lookup, service):
    """ Given the lookup type and a function to generate to the lookup text, query database for spotify track ids """
    if not metadata:
        return metadata, {}

    lookups = []
    for idx, item in metadata.items():
        text = generate_lookup(item)
        lookup = unidecode(re.sub(r'[^\w]+', '', text).lower())
        lookups.append((idx, lookup))

    index = query_combined_lookup(column, lookups, service)

    remaining_items = {}
    for idx, item in metadata.items():
        track_ids = index.get(idx)
        if track_ids:
            if service == 'spotify':
                metadata[idx]["spotify_track_ids"] = track_ids
            else:
                metadata[idx]["apple_track_ids"] = track_ids
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


def lookup_using_metadata(params: list[dict], service):
    """ Given a list of dicts each having artist name, release name and track name, attempt to find spotify track
    id for each. """
    all_metadata, metadata = {}, {}
    for idx, item in enumerate(params):
        all_metadata[idx] = item
        if "artist_name" in item and "track_name" in item:
            metadata[idx] = item

    # first attempt matching on artist, track and release followed by trying various detunings for unmatched recordings
    _, remaining_items = perform_lookup(LookupType.ALL, metadata, combined_all, service)
    _, remaining_items = perform_lookup(LookupType.ALL, remaining_items, combined_all_detuned, service)
    _, remaining_items = perform_lookup(LookupType.WITHOUT_ALBUM, remaining_items, combined_without_album, service)
    _, remaining_items = perform_lookup(LookupType.WITHOUT_ALBUM, remaining_items, combined_without_album_detuned, service)

    # to the still unmatched recordings, add null value so that each item has in the response has spotify_track_id key
    for item in all_metadata.values():
        if service == "spotify" and "spotify_track_ids" not in item:
            item["spotify_track_ids"] = []
        elif service == "apple_music" and "apple_track_ids" not in item:
            item["apple_track_ids"] = []
    if service == "spotify":
        return [SpotifyIdFromMBIDOutput(**row) for row in metadata.values()]
    else:
        return [AppleMusicIdFromMBIDOutput(**row) for row in metadata.values()]
