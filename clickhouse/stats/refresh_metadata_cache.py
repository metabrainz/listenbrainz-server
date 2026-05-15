"""
Refresh ClickHouse metadata tables directly from MusicBrainz PostgreSQL.

Canonical MusicBrainz entities are keyed by their positive integer MB IDs.
Submitted/unmapped entities are inserted by listen ingestion using UInt64
sipHash IDs. Both ID spaces share the same metadata tables.
"""

import json
import logging
import time

import psycopg2
import pycountry

from clickhouse.stats.schema import ensure_stats_schema
from data.postgres.release import get_release_metadata_cache_query
from data.postgres.release_group import get_release_group_metadata_cache_query

logger = logging.getLogger(__name__)

COUNTRY_ALPHA_2_TO_3 = {c.alpha_2: c.alpha_3 for c in pycountry.countries}


TABLE_NAMES = {
    "artist": "artist_metadata",
    "recording": "recording_metadata",
    "release": "release_metadata",
    "release_group": "release_group_metadata",
}

COLUMN_NAMES = {
    "artist": ["artist_id", "artist_mbid", "artist_name", "country_code"],
    "recording": [
        "recording_id", "recording_mbid", "recording_name", "artist_name",
        "artist_credit_mbids", "release_name", "release_mbid", "artists",
        "caa_id", "caa_release_mbid",
    ],
    "release": [
        "release_id", "release_mbid", "release_group_id", "release_group_mbid",
        "first_release_date_year", "release_name", "album_artist_name",
        "caa_id", "caa_release_mbid", "artist_credit_mbids", "artists",
    ],
    "release_group": [
        "release_group_id", "release_group_mbid", "release_group_name", "artist_name",
        "caa_id", "caa_release_mbid", "artist_credit_mbids", "artists",
        "first_release_date_year", "primary_type",
    ],
}


def get_artist_metadata_query():
    return """
        SELECT DISTINCT ON (artist_id)
               artist_id
             , artist_mbid
             , artist_name
             , country_code_alpha_2
          FROM (
            SELECT a.id AS artist_id
                 , a.gid::text AS artist_mbid
                 , a.name AS artist_name
                 , iso.code AS country_code_alpha_2
                 , 1 AS priority
              FROM musicbrainz.artist a
              JOIN musicbrainz.iso_3166_1 iso
                ON iso.area = a.area
             UNION
            SELECT a.id AS artist_id
                 , a.gid::text AS artist_mbid
                 , a.name AS artist_name
                 , iso.code AS country_code_alpha_2
                 , 2 AS priority
              FROM musicbrainz.artist a
              JOIN musicbrainz.area_containment ac
                ON ac.descendant = a.area
              JOIN musicbrainz.iso_3166_1 iso
                ON iso.area = ac.parent
             UNION
            SELECT a.id AS artist_id
                 , a.gid::text AS artist_mbid
                 , a.name AS artist_name
                 , NULL AS country_code_alpha_2
                 , 3 AS priority
              FROM musicbrainz.artist a
             WHERE a.area IS NULL
          ) t
      ORDER BY artist_id, priority
    """


def get_recording_metadata_query():
    return """
        SELECT r.id AS recording_id
             , r.gid::text AS recording_mbid
             , r.name AS recording_name
             , ac.name AS artist_name
             , array_agg(a.gid::text ORDER BY acn.position) AS artist_credit_mbids
             , '' AS release_name
             , '' AS release_mbid
             , jsonb_agg(
                    jsonb_build_object(
                        'artist_credit_name', acn.name,
                        'join_phrase', acn.join_phrase,
                        'artist_mbid', a.gid::text
                    )
                    ORDER BY acn.position
               ) AS artists
             , 0 AS caa_id
             , '' AS caa_release_mbid
          FROM musicbrainz.recording r
          JOIN musicbrainz.artist_credit ac
            ON ac.id = r.artist_credit
          JOIN musicbrainz.artist_credit_name acn
            ON acn.artist_credit = r.artist_credit
          JOIN musicbrainz.artist a
            ON a.id = acn.artist
      GROUP BY r.id, r.gid, r.name, ac.name
    """


def get_release_metadata_query():
    return f"""
        SELECT rel.id AS release_id
             , src.release_mbid
             , rg.id AS release_group_id
             , src.release_group_mbid
             , src.first_release_date_year
             , src.release_name
             , src.album_artist_name
             , src.caa_id
             , src.caa_release_mbid
             , src.artist_credit_mbids
             , src.artists
          FROM ({get_release_metadata_cache_query()}) src
          JOIN musicbrainz.release rel
            ON rel.gid = src.release_mbid::uuid
          JOIN musicbrainz.release_group rg
            ON rg.gid = src.release_group_mbid::uuid
    """


def get_release_group_metadata_query():
    return f"""
        SELECT rg.id AS release_group_id
             , src.release_group_mbid
             , src.title AS release_group_name
             , src.artist_credit_name AS artist_name
             , src.caa_id
             , src.caa_release_mbid
             , src.artist_credit_mbids
             , src.artists
             , src.first_release_date_year
             , src.primary_type
          FROM ({get_release_group_metadata_cache_query()}) src
          JOIN musicbrainz.release_group rg
            ON rg.gid = src.release_group_mbid::uuid
    """


PG_QUERIES = {
    "artist": get_artist_metadata_query(),
    "recording": get_recording_metadata_query(),
    "release": get_release_metadata_query(),
    "release_group": get_release_group_metadata_query(),
}


def _to_json_str(val):
    if val is None:
        return "[]"
    if isinstance(val, str):
        return val
    return json.dumps(val)


def _clean_array(val):
    if val is None:
        return []
    return [str(v) for v in val if v is not None]


def _transform_artist(row):
    artist_id, artist_mbid, artist_name, country_code_alpha_2 = row
    country_code = COUNTRY_ALPHA_2_TO_3.get(country_code_alpha_2, "") if country_code_alpha_2 else ""
    return (artist_id or 0, artist_mbid or "", artist_name or "", country_code)


def _transform_recording(row):
    (recording_id, recording_mbid, recording_name, artist_name,
     artist_credit_mbids, release_name, release_mbid, artists,
     caa_id, caa_release_mbid) = row
    return (
        recording_id or 0,
        recording_mbid or "",
        recording_name or "",
        artist_name or "",
        _clean_array(artist_credit_mbids),
        release_name or "",
        release_mbid or "",
        _to_json_str(artists),
        caa_id or 0,
        str(caa_release_mbid) if caa_release_mbid else "",
    )


def _transform_release(row):
    (release_id, release_mbid, release_group_id, release_group_mbid, first_release_date_year,
     release_name, album_artist_name, caa_id, caa_release_mbid,
     artist_credit_mbids, artists) = row
    return (
        release_id or 0,
        release_mbid or "",
        release_group_id or 0,
        str(release_group_mbid) if release_group_mbid else "",
        first_release_date_year or 0,
        release_name or "",
        album_artist_name or "",
        caa_id or 0,
        str(caa_release_mbid) if caa_release_mbid else "",
        _clean_array(artist_credit_mbids),
        _to_json_str(artists),
    )


def _transform_release_group(row):
    (release_group_id, release_group_mbid, title, artist_credit_name, caa_id,
     caa_release_mbid, artist_credit_mbids, artists,
     first_release_date_year, primary_type) = row
    return (
        release_group_id or 0,
        release_group_mbid or "",
        title or "",
        artist_credit_name or "",
        caa_id or 0,
        str(caa_release_mbid) if caa_release_mbid else "",
        _clean_array(artist_credit_mbids),
        _to_json_str(artists),
        first_release_date_year or 0,
        primary_type or "",
    )


TRANSFORMS = {
    "artist": _transform_artist,
    "recording": _transform_recording,
    "release": _transform_release,
    "release_group": _transform_release_group,
}


def refresh_cache(cache_type, pg_dsn, ch_client, batch_size=100_000):
    """Refresh a single metadata table from MusicBrainz PostgreSQL."""
    table = TABLE_NAMES[cache_type]
    columns = COLUMN_NAMES[cache_type]
    transform = TRANSFORMS[cache_type]

    ensure_stats_schema(ch_client)
    # Preserve submitted rows; refreshed canonical rows supersede older ones via ReplacingMergeTree.

    total_rows = 0
    start = time.monotonic()

    with psycopg2.connect(pg_dsn) as pg_conn:
        with pg_conn.cursor(name=f"{cache_type}_cache_cursor") as cursor:
            cursor.execute(PG_QUERIES[cache_type])
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                ch_client.insert(table, [transform(row) for row in rows], column_names=columns)
                total_rows += len(rows)

    elapsed = time.monotonic() - start
    logger.info("Refreshed %s: %d rows in %.1fs", table, total_rows, elapsed)
    return total_rows


def refresh_metadata_caches(pg_dsn, ch_client, cache_types=None, batch_size=100_000):
    """
    Refresh all (or selected) metadata tables.

    Returns a dict mapping cache_type -> row count (or -1 on error).
    """
    if cache_types is None:
        cache_types = list(PG_QUERIES.keys())

    results = {}
    for cache_type in cache_types:
        try:
            results[cache_type] = refresh_cache(cache_type, pg_dsn, ch_client, batch_size)
        except Exception:
            logger.error("Error refreshing %s cache", cache_type, exc_info=True)
            results[cache_type] = -1
    return results
