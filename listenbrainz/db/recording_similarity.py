from uuid import UUID

from psycopg2.extras import execute_values, DictCursor
from psycopg2.sql import SQL, Literal

from listenbrainz.db import timescale


def insert_similar_recordings(data, algorithm):
    """ Insert similar recordings in database """
    query = """
        INSERT INTO similarity.recording AS sr (mbid0, mbid1, metadata)
             VALUES %s
        ON CONFLICT (mbid0, mbid1)
          DO UPDATE
                SET metadata = sr.metadata || EXCLUDED.metadata
    """
    values = [(x["mbid0"], x["mbid1"], x["score"]) for x in data]
    template = SQL("(%s, %s, jsonb_build_object({algorithm}, %s))").format(algorithm=Literal(algorithm))

    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            execute_values(curs, query, values, template)
        conn.commit()
    finally:
        conn.close()


def get_similar_recordings(mbids, algorithm, count):
    """ Fetch at most `count` number of similar recordings for each mbid in the given
     list using the given algorithm. """
    query = SQL("""
        WITH mbids(mbid) AS (
            VALUES %s
        ), intermediate AS (
            SELECT mbid
                 , CASE WHEN mbid0 = mbid THEN mbid1 ELSE mbid0 END AS similar_mbid
                 , jsonb_object_field(metadata, {algorithm})::integer AS score
              FROM similarity.recording
              JOIN mbids
                ON TRUE
             WHERE (mbid0 = mbid OR mbid1 = mbid)
               AND metadata ? {algorithm}
        ), ordered AS (
            SELECT mbid
                 , similar_mbid
                 , score
                 , row_number() over (PARTITION BY mbid ORDER BY score DESC) AS rnum
              FROM intermediate
        )   SELECT mbid
                 , similar_mbid
                 , score
              FROM ordered
             WHERE rnum <= {count}
    """).format(algorithm=Literal(algorithm), count=Literal(count))
    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as curs:
            result = execute_values(curs, query, [(UUID(mbid),) for mbid in mbids], fetch=True)
            return result
    finally:
        conn.close()
