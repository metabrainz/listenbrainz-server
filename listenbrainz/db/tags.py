from collections import defaultdict

from psycopg2.extras import execute_values
from psycopg2.sql import Literal, SQL
from sqlalchemy import text

from listenbrainz.db import timescale


def insert(source, recordings):
    values = []
    for rec in recordings:
        tags = [(rec["recording_mbid"], tag["tag"], tag["tag_count"], tag["_percent"]) for tag in rec["tags"]]
        values.extend(tags)

    query = "INSERT INTO tags.tags (recording_mbid, tag, tag_count, percent, source) VALUES %s"

    template = SQL("(%s, %s, %s, %s, {source})").format(source=Literal(source))
    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            execute_values(curs, query, values, template)
        conn.commit()
    finally:
        conn.close()


def get(connection, query, count_query, params, results, counts):
    rows = connection.execute(text(query), params)
    for row in rows:
        source = row["source"]
        results[source].extend(row["recordings"])

    rows = connection.execute(text(count_query), params)
    for row in rows:
        source = row["source"]
        counts[source] += row["total_count"]


def get_and(tags, begin_percent, end_percent, count):
    results = defaultdict(list)
    counts = defaultdict(int)

    params = {"count": count, "begin_percent": begin_percent, "end_percent": end_percent}

    clauses = []
    for idx, tag in enumerate(tags):
        param = f"tag_{idx}"
        params[param] = tag
        clauses.append(f"""
            SELECT recording_mbid
                 , source
              FROM tags.tags
             WHERE tag = :{param}
               AND :begin_percent <= percent
               AND percent < :end_percent
        """)
    clause = " INTERSECT ".join(clauses)

    query = f"""
        WITH all_recs AS (
            {clause}
         ), randomize_recs AS (
            SELECT recording_mbid
                 , source
                 , row_number() OVER (PARTITION BY source ORDER BY RANDOM()) AS rnum
              FROM all_recs    
         ), selected_recs AS (
            SELECT recording_mbid
                 , source
              FROM randomize_recs
             WHERE rnum <= :count
        )   SELECT source
                 , jsonb_agg(
                        jsonb_build_object(
                            'recording_mbid'
                           , recording_mbid
                           , 'tag_count'
                           , tag_count
                           , 'percent'
                           , percent
                        )
                   ) AS recordings
              FROM selected_recs
              JOIN tags.tags
             USING (recording_mbid, source)
             WHERE tag = :tag_0
          GROUP BY source
    """

    count_query = f"""
        WITH all_recs AS (
            {clause}
         ) SELECT source
                , count(*) AS total_count
             FROM all_recs
         GROUP BY source
    """

    more_clauses = []
    for idx, tag in enumerate(tags):
        param = f"tag_{idx}"
        params[param] = tag
        more_clauses.append(f"""
            SELECT recording_mbid
                 , source
              FROM tags.tags
             WHERE tag = :{param}
               AND (percent < :begin_percent
                OR percent >= :end_percent)
        """)
    more_clause = " INTERSECT ".join(clauses)

    more_query = f"""
        WITH all_recs AS (
            {more_clause}
         ), randomize_recs AS (
            SELECT recording_mbid
                 , source
                 , row_number() OVER (PARTITION BY source ORDER BY RANDOM()) AS rnum
              FROM all_recs    
         ), selected_recs AS (
            SELECT recording_mbid
                 , source
              FROM randomize_recs
             WHERE rnum <= :count
        )   SELECT source
                 , jsonb_agg(
                        jsonb_build_object(
                            'recording_mbid'
                           , recording_mbid
                           , 'tag_count'
                           , tag_count
                           , 'percent'
                           , percent
                        )
                   ) AS recordings
              FROM selected_recs
              JOIN tags.tags
             USING (recording_mbid, source)
             WHERE tag = :tag_0
          GROUP BY source
    """

    more_count_query = f"""
        WITH all_recs AS (
            {more_clause}
         ) SELECT source
                , count(*) AS total_count
             FROM all_recs
         GROUP BY source
    """

    with timescale.engine.connect() as connection:
        get(connection, query, count_query, params, results, counts)
        if len(results["artist"]) < count or len(results["recording"]) < count or len(results["release-group"]) < count:
            get(connection, more_query, more_count_query, params, results, counts)

    results["count"] = counts
    return results


def get_or(tags, begin_percent, end_percent, count):
    """ Retrieve the recordings for any of the given tags within the percent bounds. """
    results = defaultdict(list)
    counts = defaultdict(int)

    query = """
        WITH all_tags AS (
            SELECT tag
                 , recording_mbid
                 , tag_count
                 , percent
                 , source
                 , row_number() OVER (PARTITION BY source ORDER BY RANDOM()) AS rnum
              FROM tags.tags
             WHERE tag IN :tags
               AND :begin_percent <= percent
               AND percent < :end_percent
        )   SELECT source
                 , jsonb_agg(
                        jsonb_build_object(
                            'recording_mbid'
                           , recording_mbid
                           , 'tag_count'
                           , tag_count
                           , 'percent'
                           , percent
                        )
                   ) AS recordings
              FROM all_tags
             WHERE rnum <= :count
          GROUP BY source
    """

    count_query = """
        SELECT source
             , count(*) AS total_count
          FROM tags.tags
         WHERE tag IN :tags
           AND :begin_percent <= percent
           AND percent < :end_percent
      GROUP BY source
    """

    more_query = """
        WITH all_tags AS (
            SELECT tag
                 , recording_mbid
                 , tag_count
                 , percent
                 , source
                 , row_number() OVER (
                        PARTITION BY source
                            ORDER BY CASE 
                                     WHEN :begin_percent > percent THEN percent - :begin_percent
                                     WHEN :end_percent < percent THEN :end_percent - percent
                                     ELSE 1
                                     END
                                   , RANDOM()
                   ) AS rnum
              FROM tags.tags
             WHERE tag IN :tags
               AND (percent < :begin_percent
                OR percent >= :end_percent)
        )   SELECT source
                 , jsonb_agg(
                        jsonb_build_object(
                            'recording_mbid'
                           , recording_mbid
                           , 'tag_count'
                           , tag_count
                           , 'percent'
                           , percent
                        )
                   ) AS recordings
              FROM all_tags
             WHERE rnum <= :count
          GROUP BY source
    """

    more_count_query = """
        SELECT source
             , count(*) AS total_count
          FROM tags.tags
         WHERE tag IN :tags
           AND (percent < :begin_percent
            OR percent >= :end_percent)
      GROUP BY source
    """

    params = {
        "tags": tuple(tags),
        "begin_percent": begin_percent,
        "end_percent": end_percent,
        "count": count
    }

    with timescale.engine.connect() as connection:
        get(connection, query, count_query, params, results, counts)
        if len(results["artist"]) < count or len(results["recording"]) < count or len(results["release-group"]) < count:
            get(connection, more_query, more_count_query, params, results, counts)

    results["count"] = counts
    return results
