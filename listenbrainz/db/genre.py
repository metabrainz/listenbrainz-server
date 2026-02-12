import psycopg2
from brainzutils import cache
from flask import current_app
from psycopg2.extras import DictCursor
from typing import Any, Iterable

TAG_HEIRARCHY_CACHE_KEY = "tag_hierarchy"

# Entity types that have tags in MusicBrainz: (entity_type, tag_table, id_column, order_column, limit).
# order_column: artist uses sort_name, others use name (per MusicBrainz EntityTag role).
TAGGED_ENTITY_TYPES = [
    ("artist", "artist_tag", "artist", "sort_name", 12),
    ("release_group", "release_group_tag", "release_group", "name", 100),
    ("recording", "recording_tag", "recording", "name", 12),
]
TAG_HEIRARCHY_CACHE_EXPIRY = 60 * 60 * 24 * 7  # 7 days


def load_genre_with_subgenres(mb_curs: DictCursor):
    query = """
        SELECT
            g1.name as genre,
            g1.gid::text as genre_gid,
            g2.name as subgenre,
            g2.gid::text as subgenre_gid
        FROM genre g1
        LEFT JOIN (
            SELECT entity0, entity1
            FROM l_genre_genre lgg
            WHERE lgg.link IN (
                SELECT id
                FROM link
                WHERE link_type = 1095
            )
        ) lgg ON g1.id = lgg.entity0
        LEFT JOIN genre g2 ON lgg.entity1 = g2.id
        ORDER BY g1.name, COALESCE(g2.name, '');
    """

    mb_curs.execute(query)
    return mb_curs.fetchall()


def search_genres(mb_curs, query: str, limit: int = 50):
    """Search MusicBrainz genre table by name (case-insensitive).
    Orders by: exact match first, then prefix match, then contains; then by name.
    Returns list of dicts with gid, name."""
    if not query or not query.strip():
        return []
    query_clean = query.strip()
    pattern = f"%{query_clean}%"
    prefix_pattern = f"{query_clean}%"
    mb_curs.execute(
        """
        SELECT gid::text AS gid, name
          FROM genre
         WHERE name ILIKE %s
         ORDER BY
           (LOWER(TRIM(name)) = LOWER(%s)) DESC,
           (LOWER(name) LIKE LOWER(%s)) DESC,
           name
         LIMIT %s
        """,
        (pattern, query_clean, prefix_pattern, limit),
    )
    return [dict(row) for row in mb_curs.fetchall()]


def get_tag_hierarchy_data():
    data = cache.get(TAG_HEIRARCHY_CACHE_KEY)
    if not data:
        with (
            psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn,
            mb_conn.cursor(cursor_factory=DictCursor) as mb_curs
        ):
            data = load_genre_with_subgenres(mb_curs)
            data = [dict(row) for row in data] if data else []
        cache.set(TAG_HEIRARCHY_CACHE_KEY, data, expirein=TAG_HEIRARCHY_CACHE_EXPIRY)
    return data

def load_genres_from_mbids(mb_curs: DictCursor, mbids: Iterable[str]):
    """ Given a list of mbids return a map with mbid as key and the genre info as value. """

    if not mbids:
        return {}
    
    query = """
        SELECT
            g.name as name,
            g.gid::text as genre_gid
        FROM genre g
        LEFT JOIN genre_alias ga
         on g.id = ga.genre
        WHERE g.gid::text IN %s
    """
    mb_curs.execute(query, (tuple(mbids),))
    return {row["genre_gid"]: row for row in mb_curs.fetchall()}


def get_tag_id_by_name(mb_curs: DictCursor, tag_name: str) -> int | None:
    """Resolve a tag name (e.g. genre name) to MusicBrainz tag id. Returns None if not found."""
    if not tag_name or not tag_name.strip():
        return None
    mb_curs.execute(
        """
        SELECT id FROM musicbrainz.tag
        WHERE LOWER(name) = LOWER(%s)
        LIMIT 1
        """,
        (tag_name.strip(),),
    )
    row = mb_curs.fetchone()
    return row["id"] if row else None


def find_tagged_entities(
    mb_curs: DictCursor,
    tag_name: str,
    limits: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Fetch top tagged entities from MusicBrainz for a given tag name (e.g. genre name).
    One query per entity type (artist, release_group, recording), ordered by tag count
    descending then by name/sort_name, same pattern as MusicBrainz tag index.
    Returns a dict keyed by entity type, each value: {"count": int, "entities": [{"mbid", "name", "tag_count"}, ...]}.
    limits: optional dict of entity_type -> limit; defaults from TAGGED_ENTITY_TYPES.
    """
    tag_id = get_tag_id_by_name(mb_curs, tag_name)
    if tag_id is None:
        return {
            entity_type: {"count": 0, "entities": []}
            for entity_type, _tag_table, _id_col, _order_col, _limit in TAGGED_ENTITY_TYPES
        }

    override_limits = limits or {}
    result: dict[str, Any] = {}
    for entity_type, tag_table, id_column, order_column, default_limit in TAGGED_ENTITY_TYPES:
        limit = override_limits.get(entity_type, default_limit)
        # Table names in MusicBrainz: artist, release_group, recording
        entity_table = "release_group" if entity_type == "release_group" else entity_type
        query = f"""
            SELECT
                e.gid::text AS mbid,
                e.name AS name,
                tt.count AS tag_count
            FROM musicbrainz.{entity_table} e
            JOIN musicbrainz.{tag_table} tt ON e.id = tt.{id_column}
            WHERE tt.tag = %s AND tt.count > 0
            ORDER BY tt.count DESC, e.{order_column} COLLATE musicbrainz, e.id
            LIMIT %s OFFSET 0
        """
        mb_curs.execute(query, (tag_id, limit))
        rows = mb_curs.fetchall()
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM musicbrainz.{tag_table} tt
            WHERE tt.tag = %s AND tt.count > 0
        """
        mb_curs.execute(count_query, (tag_id,))
        total = mb_curs.fetchone()["total"]

        result[entity_type] = {
            "count": total,
            "entities": [
                {
                    "mbid": row["mbid"],
                    "name": row["name"],
                    "tag_count": row["tag_count"],
                }
                for row in rows
            ],
        }
    return result

