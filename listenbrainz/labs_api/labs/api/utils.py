from contextlib import closing
import re
from enum import Enum

import psycopg2

from flask import current_app
from pydantic import BaseModel
from unidecode import unidecode
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Identifier

from listenbrainz.db import timescale
from listenbrainz.db.recording import resolve_redirect_mbids, resolve_canonical_mbids


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
    elif service == 'apple_music':
        table = 'mapping.apple_metadata_index'
    elif service == 'soundcloud':
        table = 'mapping.soundcloud_metadata_index'
    else:
        raise ValueError("Service must be either 'spotify', 'apple_music' or 'soundcloud'")

    query = SQL("""
          WITH lookups (idx, value) AS (VALUES %s)
        SELECT DISTINCT ON ({column})
               idx, array_agg(track_id ORDER BY score DESC) AS track_ids
          FROM lookups
          JOIN {table}
            ON {column} = value
      GROUP BY {column}, idx      
    """).format(column=Identifier(column.value), table=SQL(table))

    with closing(timescale.engine.raw_connection()) as conn, conn.cursor() as curs:
        execute_values(curs, query, lookups, page_size=len(lookups))
        result = curs.fetchall()
        return {row[0]: row[1] for row in result}


def perform_lookup(column, metadata, generate_lookup, service, track_id_field):
    """ Given the lookup type and a function to generate to the lookup text, query database for external service track ids """
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
            metadata[idx][track_id_field] = track_ids
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


def lookup_using_metadata(params: list[dict], service, model: type[BaseModel], track_id_field: str):
    """ Given a list of dicts each having artist name, release name and track name, attempt to find external service
    track id for each. """
    all_metadata, metadata = {}, {}
    for idx, item in enumerate(params):
        all_metadata[idx] = item
        if "artist_name" in item and "track_name" in item:
            metadata[idx] = item

    # first attempt matching on artist, track and release followed by trying various detunings for unmatched recordings
    remaining_items = metadata
    # soundcloud doesn't support albums
    if service != "soundcloud":
        _, remaining_items = perform_lookup(
            LookupType.ALL,
            remaining_items,
            combined_all,
            service,
            track_id_field
        )
        _, remaining_items = perform_lookup(
            LookupType.ALL,
            remaining_items,
            combined_all_detuned,
            service,
            track_id_field
        )

    _, remaining_items = perform_lookup(
        LookupType.WITHOUT_ALBUM,
        remaining_items,
        combined_without_album,
        service,
        track_id_field
    )
    _, remaining_items = perform_lookup(
        LookupType.WITHOUT_ALBUM,
        remaining_items,
        combined_without_album_detuned,
        service,
        track_id_field
    )

    # to the still unmatched recordings, add null value so that each item has in the response has the appropriate
    # external service track ids key
    for item in all_metadata.values():
        if track_id_field not in item:
            item[track_id_field] = []
    return [model(**row) for row in metadata.values()]


def lookup_spotify_track_ids_from_mb_url_rels(mbids: list[str]) -> dict[str, list[str]]:
    """Look up Spotify track ids for the given recording MBIDs via MusicBrainz URL relationships.

    Queries curated recording -> Spotify URL links maintained by MusicBrainz editors,
    bypassing text-normalization failure modes of the metadata index.

    Args:
        mbids: Recording MBIDs to look up.

    Returns:
        Dict mapping recording_mbid to a list of Spotify track ids. Only MBIDs
        with at least one matching URL relationship are present.
    """
    if not mbids:
        return {}

    query = """
        WITH input_mbids (gid) AS (VALUES %s)
        SELECT input_mbids.gid::text AS recording_mbid,
               array_agg(DISTINCT substring(u.url FROM 'open\\.spotify\\.com/track/([A-Za-z0-9]+)')) AS track_ids
          FROM input_mbids
          JOIN musicbrainz.recording       r   ON r.gid = input_mbids.gid::uuid
          JOIN musicbrainz.l_recording_url lru ON lru.entity0 = r.id
          JOIN musicbrainz.url             u   ON u.id = lru.entity1
          JOIN musicbrainz.link            l   ON l.id = lru.link
          JOIN musicbrainz.link_type       lt  ON lt.id = l.link_type
         WHERE lt.name IN ('free streaming', 'streaming')
           AND u.url ~ '^https?://open\\.spotify\\.com/track/[A-Za-z0-9]+'
      GROUP BY input_mbids.gid
    """

    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn, conn.cursor() as curs:
        execute_values(curs, query, [(mbid,) for mbid in mbids], page_size=len(mbids))
        return {
            row[0]: [tid for tid in row[1] if tid]
            for row in curs.fetchall()
            if row[1] and any(tid for tid in row[1])
        }


def lookup_recording_canonical_metadata(mbids: list[str]):
    """ Retrieve metadata from canonical tables for given mbids. All mbids are first looked up in MB redirects
    and then resolved to canonical mbids. Finally, the metadata for canonical mbids is retrieved. """
    with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn, conn.cursor() as curs:
        redirected_mbids, redirect_index, _ = resolve_redirect_mbids(curs, "recording", mbids)

    with closing(timescale.engine.raw_connection()) as ts_conn, ts_conn.cursor() as curs:
        canonical_mbids, canonical_index, _ = resolve_canonical_mbids(curs, redirected_mbids)
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

    ordered_metadata = []
    for mbid in mbids:
        # check whether mbid was redirected before looking up metadata
        redirected_mbid = redirect_index.get(mbid, mbid)
        canonical_mbid = canonical_index.get(redirected_mbid, redirected_mbid)

        mbid_metadata = metadata.get(canonical_mbid, {})
        # regardless of whether we redirected the mbid, add the original mbid in the response returned to user
        mbid_metadata["recording_mbid"] = mbid
        ordered_metadata.append(mbid_metadata)

    return ordered_metadata
