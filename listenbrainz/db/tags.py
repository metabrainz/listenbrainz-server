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


def get(tag, begin_percent, end_percent, count):
    """ Retrieve the recordings for a given tag within the percent bounds, ordered by tag_count within it. """
    results = {
        "recording": [],
        "artist": [],
        "release-group": []
    }
    query = """
        WITH recording_tags AS (
            SELECT recording_mbid
                 , tag_count
                 , percent
                 , source
              FROM tags.tags
             WHERE tag = :tag
               AND source = 'recording'
          ORDER BY CASE 
                   WHEN :begin_percent <= percent AND percent <= :end_percent THEN 0
                   WHEN :begin_percent < percent THEN percent - :begin_percent
                   WHEN percent < :end_percent THEN :end_percent - percent
                   ELSE 1
                   END
                 , RANDOM()
             LIMIT :count
        ), artist_tags AS (
            SELECT recording_mbid
                 , tag_count
                 , percent
                 , source
              FROM tags.tags
             WHERE tag = :tag
               AND source = 'artist'
          ORDER BY CASE 
                   WHEN :begin_percent <= percent AND percent <= :end_percent THEN 0
                   WHEN :begin_percent < percent THEN percent - :begin_percent
                   WHEN percent < :end_percent THEN :end_percent - percent
                   ELSE 1
                   END
                 , RANDOM()
             LIMIT :count
        ), release_tags AS (
            SELECT recording_mbid
                 , tag_count
                 , percent
                 , source
              FROM tags.tags
             WHERE tag = :tag
               AND source = 'release-group'
          ORDER BY CASE 
                   WHEN :begin_percent <= percent AND percent <= :end_percent THEN 0
                   WHEN :begin_percent < percent THEN percent - :begin_percent
                   WHEN percent < :end_percent THEN :end_percent - percent
                   ELSE 1
                   END
                 , RANDOM()
             LIMIT :count
        )   SELECT *
              FROM recording_tags
             UNION ALL
            SELECT *
              FROM artist_tags
             UNION ALL
            SELECT *
              FROM release_tags
    """
    count_query = """
        SELECT source
             , count(*) AS total_count
          FROM tags.tags
         WHERE tag = :tag
           AND :begin_percent <= percent
           AND percent < :end_percent
      GROUP BY source     
    """
    params = {
        "tag": tag,
        "begin_percent": begin_percent,
        "end_percent": end_percent,
        "count": count
    }
    with timescale.engine.connect() as connection:
        rows = connection.execute(text(query), params)
        for row in rows:
            source = row["source"]
            results[source].append({
                "recording_mbid": row["recording_mbid"],
                "tag_count": row["tag_count"],
                "percent": row["percent"]
            })

        rows = connection.execute(text(count_query), params)

        counts = {x["source"]: x["total_count"] for x in rows}
        results["total_recording_count"] = counts.get("recording", 0)
        results["total_release-group_count"] = counts.get("release-group", 0)
        results["total_artist_count"] = counts.get("artist", 0)

    return results
