import time

from psycopg2.extras import execute_values
from psycopg2.sql import Literal, SQL, Identifier
from sqlalchemy import text

from listenbrainz.db import timescale


def start_table():
    """ Create the table to store tags dataset.

    When we start receiving the tags data, we create a temporary table to store the data. Once
    the dataset has been received completely, we switch the temporary table with the production tables.
    We do not use something like INSERT ON CONFLICT DO NOTHING to avoid mixups the last runs' results
    (like tags being deleted since then).
    """
    table = Identifier("tags", "tags_tmp")
    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            query = SQL("DROP TABLE IF EXISTS {table}").format(table=table)
            curs.execute(query)

            query = SQL("""
                CREATE TABLE {table} (
                    tag                     TEXT NOT NULL,
                    recording_mbid          UUID NOT NULL,
                    tag_count               INTEGER NOT NULL,
                    percent                 DOUBLE PRECISION NOT NULL,
                    source                  tag_source_type_enum NOT NULL
                );
            """).format(table=table)
            curs.execute(query)

        conn.commit()
    finally:
        conn.close()


def end_table():
    """ Switch the temporary production table in production. """
    incoming_table = Identifier("tags", "tags_tmp")
    # add a random suffix to the index name to avoid issues while renaming
    suffix = int(time.time())

    conn = timescale.engine.raw_connection()
    try:
        with conn.cursor() as curs:
            query = SQL("""
                CREATE INDEX tags_tag_percent_idx_{suffix} ON {table} (tag, percent)
                     INCLUDE (source, recording_mbid, tag_count)
             """).format(table=incoming_table, suffix=Literal(suffix))
            curs.execute(query)

            # rotate tables
            query = SQL("""
                ALTER TABLE {prod_table} RENAME TO {outgoing_table}
             """).format(prod_table=Identifier("tags", "tags"), outgoing_table=Identifier("tags_old"))
            curs.execute(query)
            query = SQL("""
                ALTER TABLE {incoming_table} RENAME TO {prod_table}
             """).format(incoming_table=Identifier("tags", "tags_tmp"), prod_table=Identifier("tags", "tags"))
            curs.execute(query)
            query = SQL("""DROP TABLE {old_table}""").format(old_table=Identifier("tags", "tags_old"))
            curs.execute(query)
        conn.commit()
    finally:
        conn.close()


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


def get_once(connection, query, count_query, params, results, counts):
    rows = connection.execute(text(query), params)
    for row in rows:
        source = row["source"]
        results[source].extend(row["recordings"])

    rows = connection.execute(text(count_query), params)
    for row in rows:
        source = row["source"]
        counts[source] += row["total_count"]


def get(query, count_query, more_query, more_count_query, params):
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
              FROM tags.tags
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

    return query, count_query, params


def build_or_query(expanded=True):
    order_clause, percent_clause = get_partial_clauses(expanded)

    query = f"""
        WITH all_tags AS (
            SELECT tag
                 , recording_mbid
                 , tag_count
                 , percent
                 , source
                 , row_number() OVER (PARTITION BY source {order_clause}) AS rnum
              FROM tags.tags
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
          FROM tags.tags
         WHERE tag IN :tags
           AND ({percent_clause})
      GROUP BY source
    """

    return query, count_query


def get_and(tags, begin_percent, end_percent, count):
    params = {"count": count, "begin_percent": begin_percent, "end_percent": end_percent}
    query, count_query, _params = build_and_query(tags, False)
    more_query, more_count_query, _ = build_and_query(tags, True)
    params.update(_params)
    return get(query, count_query, more_query, more_count_query, params)


def get_or(tags, begin_percent, end_percent, count):
    """ Retrieve the recordings for any of the given tags within the percent bounds. """
    params = {"tags": tuple(tags), "begin_percent": begin_percent, "end_percent": end_percent, "count": count}
    query, count_query = build_or_query(False)
    more_query, more_count_query = build_or_query(True)
    return get(query, count_query, more_query, more_count_query, params)
