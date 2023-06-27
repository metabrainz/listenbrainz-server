from psycopg2.extras import execute_values
from psycopg2.sql import Literal, SQL
from sqlalchemy import text

from listenbrainz.db import timescale


def insert(source, recordings):
    values = []
    for rec in recordings:
        tags = [(rec["recording_mbid"], tag["tag"], tag["tag_count"], tag["percent"]) for tag in rec["tags"]]
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


def get(tag, begin_percent, end_percent, count, offset):
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
                 , 'recording'
              FROM tags.tags
             WHERE tag = :tag
               AND source = ''
               AND begin_percent <= percent
               AND percent < end_percent
          ORDER BY tag_count DESC
             LIMIT :limit
            OFFSET :offset
        ), artist_tags AS (
            SELECT recording_mbid
                 , tag_count
                 , source
              FROM tags.tags
             WHERE tag = :tag
               AND source = 'artist'
               AND begin_percent <= percent
               AND percent < end_percent
          ORDER BY tag_count DESC
             LIMIT :limit
            OFFSET :offset
        ), release_tags AS (
            SELECT recording_mbid
                 , tag_count
                 , source
              FROM tags.tags
             WHERE tag = :tag
               AND source = 'release-group'
               AND begin_percent <= percent
               AND percent < end_percent
          ORDER BY tag_count DESC
             LIMIT :limit
            OFFSET :offset
        )   SELECT *
              FROM recording_tags
             UNION ALL
            SELECT *
              FROM artist_tags
             UNION ALL
            SELECT *
              FROM release_tags
          ORDER BY tag_count DESC
    """
    with timescale.engine.connect() as connection:
        rows = connection.execute(text(query))
        for row in rows:
            source = row["source"]
            results[source].append({
                "recording_mbid": row["recording_mbid"],
                "tag_count": row["tag_count"]
            })
    return results
