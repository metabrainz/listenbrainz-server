"""ClickHouse caches and the PostgreSQL queries used to populate them."""

import json
from dataclasses import dataclass

import pycountry

from data.postgres.artist import get_artist_country_cache_query
from data.postgres.artist_credit import get_artist_credit_cache_query
from data.postgres.feedback import get_feedback_cache_query
from data.postgres.recording import get_recording_artist_cache_query, get_recording_length_cache_query
from data.postgres.release import get_release_metadata_cache_query
from data.postgres.release_group import get_release_group_metadata_cache_query
from data.postgres.tag import get_tag_or_genre_cache_query


@dataclass(frozen=True)
class MetadataTable:
    name: str
    columns: str
    order_by: str
    query: str
    parameters: dict | None = None


ARTISTS = "Array(Tuple(artist_credit_name String, join_phrase String, artist_mbid UUID))"

# The country query can omit artists whose area has no ISO country.
ARTIST_METADATA_CACHE = MetadataTable(
    "artist_metadata_cache", "artist_id Int32, artist_mbid UUID, artist_name String", "artist_mbid",
    "SELECT id AS artist_id, gid AS artist_mbid, name AS artist_name FROM musicbrainz.artist",
)

MUSICBRAINZ_TABLES = (
    ARTIST_METADATA_CACHE,
    MetadataTable(
        "artist_country_cache", "artist_mbid UUID, artist_name String, country_code Nullable(String)", "artist_mbid",
        f"""
            SELECT artist_mbid, artist_name, alpha_3 AS country_code
              FROM ({get_artist_country_cache_query()}) artist_country
         LEFT JOIN jsonb_each_text(CAST(:iso_codes AS jsonb)) AS iso(alpha_2, alpha_3)
                ON country_code_alpha_2 = alpha_2
        """,
        {"iso_codes": json.dumps({c.alpha_2: c.alpha_3 for c in pycountry.countries})},
    ),
    MetadataTable(
        "artist_credit_cache", "artist_credit_id Int32, artist_mbid UUID, position Int16, join_phrase String",
        "(artist_credit_id, position)", get_artist_credit_cache_query(),
    ),
    MetadataTable(
        "recording_length_cache", "recording_mbid UUID, length Nullable(Int32), recording_id Int32, is_redirect Bool",
        "recording_mbid", get_recording_length_cache_query(),
    ),
    MetadataTable(
        "recording_artist_cache", f"recording_mbid UUID, artist_mbids Array(UUID), artists {ARTISTS}",
        "recording_mbid", get_recording_artist_cache_query(),
    ),
    MetadataTable(
        "release_metadata_cache",
        "release_mbid UUID, release_group_mbid UUID, first_release_date_year Nullable(Int16), "
        "release_name String, album_artist_name String, caa_id Nullable(Int64), caa_release_mbid Nullable(UUID), "
        f"artist_credit_mbids Array(UUID), artists {ARTISTS}",
        "release_mbid", get_release_metadata_cache_query(),
    ),
    MetadataTable(
        "release_group_metadata_cache",
        "release_group_mbid UUID, title String, artist_credit_name String, "
        "caa_id Nullable(Int64), caa_release_mbid Nullable(UUID), "
        f"artist_credit_mbids Array(UUID), artists {ARTISTS}, "
        "first_release_date_year Nullable(Int16), primary_type Nullable(String)",
        "release_group_mbid", get_release_group_metadata_cache_query(),
    ),
) + tuple(
    MetadataTable(
        f"{entity}_{kind}_cache", f"recording_mbid UUID, {kind} String, {kind}_count Int64",
        f"(recording_mbid, {kind})",
        get_tag_or_genre_cache_query(entity, only_genres=kind == "genre", with_filter=False),
    )
    for entity in ("recording", "artist", "release_group")
    for kind in ("tag", "genre")
)

RECORDING_FEEDBACK = MetadataTable(
    "recording_feedback_cache", "user_id Int32, recording_mbid Nullable(UUID), feedback Int16",
    "user_id", get_feedback_cache_query(),
)
