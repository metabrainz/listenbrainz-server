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


def get_and(tags, begin_percent, end_percent, count):
    results = {
        "recording": [],
        "artist": [],
        "release-group": []
    }

    params = {}
    clauses = []

    for idx, tag in enumerate(tags):
        param = f"tag_{idx}"
        params[param] = tag
        clauses.append(f"""
            SELECT recording_mbid
                 , source
              FROM tags.tags
             WHERE tag = :{param}
               AND percent
           BETWEEN :begin_percent
               AND :end_percent
        """)

    clause = " INTERSECT ".join(clauses)

    params.update({
        "begin_percent": begin_percent,
        "end_percent": end_percent,
        "count": count
    })

    query = text(f"""
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
         )  SELECT recording_mbid
                 , jsonb_agg(
                        jsonb_build_object(
                            'source'
                           , source
                           , 'tag_count'
                           , tag_count
                           , 'percent'
                           , percent
                        )
                   )
              FROM selected_recs
              JOIN tags.tags
             USING (recording_mbid, source)
             WHERE tag = :tag_0
          GROUP BY recording_mbid
    """)

    count_query = text(f"""
        WITH all_recs AS (
            {clause}
         ) SELECT source
                , count(*) AS total_count
             FROM all_recs
         GROUP BY source
    """)

    with timescale.engine.connect() as connection:
        rows = connection.execute(query, params)
        for row in rows:
            source = row["source"]
            results[source].append({
                "recording_mbid": row["recording_mbid"],
                "tag_count": row["tag_count"],
                "percent": row["percent"]
            })

        rows = connection.execute(count_query, params)

        counts = {x["source"]: x["total_count"] for x in rows}
        results["total_recording_count"] = counts.get("recording", 0)
        results["total_release-group_count"] = counts.get("release-group", 0)
        results["total_artist_count"] = counts.get("artist", 0)

    return results


def get_or(tags, begin_percent, end_percent, count):
    """ Retrieve the recordings for any of the given tags within the percent bounds. """
    results = {
        "recording": [],
        "artist": [],
        "release-group": []
    }

    query = text("""
        WITH all_tags AS (
            SELECT tag
                 , recording_mbid
                 , tag_count
                 , percent
                 , source
                 , row_number() OVER (PARTITION BY source, tag ORDER BY RANDOM()) AS rnum
              FROM tags.tags
             WHERE tag IN :tags
               AND percent
           BETWEEN :begin_percent
               AND :end_percent
        )   SELECT recording_mbid
                 , jsonb_agg(
                        jsonb_build_object(
                            'source'
                           , source
                           , 'tag_count'
                           , tag_count
                           , 'percent'
                           , percent
                        )
                   )
              FROM all_tags
             WHERE rnum <= :count
          GROUP BY recording_mbid
    """)
    count_query = text("""
        SELECT source
             , count(*) AS total_count
          FROM tags.tags
         WHERE tag IN :tags
           AND :begin_percent <= percent
           AND percent < :end_percent
      GROUP BY source
    """)

    params = {
        "tags": tuple(tags),
        "begin_percent": begin_percent,
        "end_percent": end_percent,
        "count": count
    }

    with timescale.engine.connect() as connection:
        rows = connection.execute(query, params)
        for row in rows:
            source = row["source"]
            results[source].append({
                "recording_mbid": row["recording_mbid"],
                "tag_count": row["tag_count"],
                "percent": row["percent"]
            })

        rows = connection.execute(count_query, params)

        counts = {x["source"]: x["total_count"] for x in rows}
        results["total_recording_count"] = counts.get("recording", 0)
        results["total_release-group_count"] = counts.get("release-group", 0)
        results["total_artist_count"] = counts.get("artist", 0)

    return results


"""
WITH all_recs AS (
    SELECT recording_mbid
         , tag_count
         , percent
         , source
      FROM tags.tags
     WHERE tag = 'rock'
       AND source = 'recording'
 INTERSECT
    SELECT recording_mbid
         , tag_count
         , percent
         , source
      FROM tags.tags
     WHERE tag = 'electronic'
       AND source = 'recording'
) SELECT * FROM all_recs
  ORDER BY RANDOM()
     LIMIT 5
"""

"""
    WITH recordings AS (
       SELECT recording_mbid
            , tag
            , row_number() OVER (PARTITION BY recording_mbid ORDER BY tag) AS rnum
            , random() AS rand
         FROM tags.tags
        WHERE tag in ('rock', 'electronic')
     GROUP BY recording_mbid, tag
  )
       SELECT recording_mbid
         FROM recordings recs
       WHERE recs.rnum = 2 
     ORDER BY recs.rand
        LIMIT 5
"""
