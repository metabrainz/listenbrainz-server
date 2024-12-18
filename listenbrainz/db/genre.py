from psycopg2.extras import DictCursor


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
