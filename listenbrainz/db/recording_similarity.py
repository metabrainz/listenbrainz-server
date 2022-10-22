from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal
from sqlalchemy import text

from listenbrainz.db import timescale


def insert_similar_recordings(data, algorithm):
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


def get_similar_recordings(mbid, algorithm, count):
    query = """
        SELECT CASE WHEN mbid0 = :mbid THEN mbid1 ELSE mbid0 END AS similar_mbid
             , jsonb_object_field(metadata, :algorithm)::integer AS score
          FROM similarity.recording
         WHERE (mbid0 = :mbid OR mbid1 = :mbid)
           AND metadata ? :algorithm
      ORDER BY score DESC
         LIMIT :count
    """
    with timescale.engine.connect() as conn:
        result = conn.execute(text(query), {"mbid": mbid, "algorithm": algorithm, "count": count})
        return result.fetchall()
