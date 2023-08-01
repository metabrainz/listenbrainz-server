from psycopg2.sql import Literal, SQL
from sqlalchemy import text

from listenbrainz.db import timescale
from listenbrainz.spark.spark_dataset import DatabaseDataset


class _TagsDataset(DatabaseDataset):

    def __init__(self):
        super().__init__("tags_dataset", "lb_tag_radio", schema="tags")

    def get_table(self):
        return """
            CREATE TABLE {table} (
                    tag                     TEXT NOT NULL,
                    recording_mbid          UUID NOT NULL,
                    tag_count               INTEGER NOT NULL,
                    percent                 DOUBLE PRECISION NOT NULL,
                    source                  tag_source_type_enum NOT NULL
            )
        """

    def get_indices(self):
        return [
            """CREATE INDEX tags_lb_tag_radio_percent_idx_{suffix} ON {table} (tag, percent)
                    INCLUDE (source, recording_mbid, tag_count)
            """
        ]

    def get_inserts(self, message):
        query = "INSERT INTO {table} (recording_mbid, tag, tag_count, percent, source) VALUES %s"

        template = SQL("(%s, %s, %s, %s, {source})").format(source=Literal(message["source"]))
        values = []
        for rec in message["recordings"]:
            tags = [(rec["recording_mbid"], tag["tag"], tag["tag_count"], tag["_percent"]) for tag in rec["tags"]]
            values.extend(tags)

        return query, template, values


TagsDataset = _TagsDataset()


def get_once(connection, query, count_query, params, results, counts):
    """ One pass over the lb radio tags dataset to retrieve matching recordings """
    rows = connection.execute(text(query), params)
    for row in rows:
        source = row["source"]
        results[source].extend(row["recordings"])

    rows = connection.execute(text(count_query), params)
    for row in rows:
        source = row["source"]
        counts[source] += row["total_count"]


def get(query, count_query, more_query, more_count_query, params):
    """ Retrieve recordings and tags for the given query. First it tries to retrieve recordings matching the
        specified criteria. If there are not enough recordings matching the given criteria, it relaxes the
        percentage bounds and to gather and return more recordings.
    """
    results = {"artist": [], "recording": [], "release-group": []}
    counts = {"artist": 0, "recording": 0, "release-group": 0}

    count = params["count"]

    with timescale.engine.connect() as connection:
        get_once(connection, query, count_query, params, results, counts)
        if len(results["artist"]) < count or len(results["recording"]) < count or len(results["release-group"]) < count:
            get_once(connection, more_query, more_count_query, params, results, counts)

    results["count"] = counts
    return results


def get_partial_clauses(expanded):
    """ The ORDER BY and WHERE clauses for the query to retrieve tags.

    expanded = False: returns a query for retrieving tags that explicitly match the requested percentage criteria
    expanded = True: returns a query for retrieving tags that do not match the requested percentage criteria but
    are centered around it.
    """
    if expanded:
        order_clause = """
            ORDER BY CASE 
                     WHEN :begin_percent > percent THEN percent - :begin_percent
                     WHEN :end_percent < percent THEN :end_percent - percent
                     ELSE 1
                     END
                   , RANDOM()
        """
        percent_clause = ":begin_percent <= percent AND percent < :end_percent"
    else:
        order_clause = "ORDER BY RANDOM()"
        percent_clause = "percent < :begin_percent OR percent >= :end_percent"

    return order_clause, percent_clause


def build_and_query(tags, expanded):
    """ Generate the query for fetching recordings when combining tags with AND """
    order_clause, percent_clause = get_partial_clauses(expanded)

    params = {}
    clauses = []

    for idx, tag in enumerate(tags):
        param = f"tag_{idx}"
        params[param] = tag
        clauses.append(f"""
            SELECT recording_mbid
                 , source
                 , percent
              FROM tags.lb_tag_radio
             WHERE tag = :{param}
               AND ({percent_clause})
        """)

    clause = " INTERSECT ".join(clauses)
    query = f"""
        WITH all_recs AS (
            {clause}
         ), randomize_recs AS (
            SELECT recording_mbid
                 , source
                 , row_number() OVER (PARTITION BY source {order_clause}) AS rnum
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
                        ORDER BY tag_count DESC
                   ) AS recordings
              FROM selected_recs
              JOIN tags.lb_tag_radio
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

    return query, count_query, params


def build_or_query(expanded=True):
    """ Generate the query for fetching recordings when combining tags with OR """
    order_clause, percent_clause = get_partial_clauses(expanded)

    query = f"""
        WITH all_tags AS (
            SELECT tag
                 , recording_mbid
                 , tag_count
                 , percent
                 , source
                 , row_number() OVER (PARTITION BY source {order_clause}) AS rnum
              FROM tags.lb_tag_radio
             WHERE tag IN :tags
               AND ({percent_clause})
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
                        ORDER BY tag_count DESC
                   ) AS recordings
              FROM all_tags
             WHERE rnum <= :count
          GROUP BY source
    """

    count_query = f"""
        SELECT source
             , count(*) AS total_count
          FROM tags.lb_tag_radio
         WHERE tag IN :tags
           AND ({percent_clause})
      GROUP BY source
    """

    return query, count_query


def get_and(tags, begin_percent, end_percent, count):
    """ Returns count number of recordings which have been tagged with all the specified tags and fall within
        the percent bounds (if less than count number of recordings satisfy the criteria, recordings that fall
        outside the percent bounds may also be returned.)
    """
    params = {"count": count, "begin_percent": begin_percent, "end_percent": end_percent}
    query, count_query, _params = build_and_query(tags, False)
    more_query, more_count_query, _ = build_and_query(tags, True)
    params.update(_params)
    return get(query, count_query, more_query, more_count_query, params)


def get_or(tags, begin_percent, end_percent, count):
    """ Returns count number of recordings which have been tagged with any of specified tags and fall within
        the percent bounds (if less than count number of recordings satisfy the criteria, recordings that fall
        outside the percent bounds may also be returned.)
    """
    params = {"tags": tuple(tags), "begin_percent": begin_percent, "end_percent": end_percent, "count": count}
    query, count_query = build_or_query(False)
    more_query, more_count_query = build_or_query(True)
    return get(query, count_query, more_query, more_count_query, params)
