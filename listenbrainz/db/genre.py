import psycopg2
from brainzutils import cache
from flask import current_app
from psycopg2.extras import DictCursor

TAG_HEIRARCHY_CACHE_KEY = "tag_hierarchy"
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
