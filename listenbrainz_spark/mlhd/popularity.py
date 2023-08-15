from more_itertools import chunked

from listenbrainz_spark import config
from listenbrainz_spark.path import MLHD_PLUS_DATA_DIRECTORY
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_dump

STATS_PER_MESSAGE = 10000


def generate_popularity_stats(name, query):
    """ Execute the given query and generate statistics. """
    df = run_query(query)
    df\
        .write\
        .format('parquet')\
        .save(config.HDFS_CLUSTER_URI + "/" + name, mode="overwrite")

    itr = df.toLocalIterator()

    for rows in chunked(itr, STATS_PER_MESSAGE):
        entries = []
        for row in rows:
            entry = row.asDict(recursive=True)
            entries.append(entry)

        yield {
            "type": name,
            "data": entries
        }


def get_popularity_query(entity, mlhd_table, listens_table):
    """ Get the query to generate popularity stats using both MLHD+ and listens data """
    entity_mbid = f"{entity}_mbid"
    return f"""
        WITH mlhd_table AS (
            SELECT {entity_mbid}
                 , count(*) AS listen_count
                 , count(distinct user_id) AS user_count
              FROM {mlhd_table}
          GROUP BY {entity_mbid}
        ), listens_table AS (
            SELECT {entity_mbid}
                 , count(*) AS listen_count
                 , count(distinct user_id) AS user_count
              FROM {listens_table}
          GROUP BY {entity_mbid}
        )   SELECT {entity_mbid}
                 , m.listen_count + l.listen_count AS total_listen_count
                 , m.user_count + l.user_count AS total_user_count
              FROM mlhd_table m
              JOIN listens_table l
             USING ({entity_mbid})
    """


def get_popularity_per_artist_query(entity, mlhd_table, listens_table):
    """ Get the query to generate top popular entities per artists stats from MLHD+ and listens data """
    if entity == "artist":
        select_clause = "artist_mbid"
        explode_clause = "explode(artist_credit_mbids) AS artist_mbid"
    else:
        entity_mbid = f"{entity}_mbid"
        select_clause = f"artist_mbid, {entity_mbid}"
        explode_clause = f"explode(artist_credit_mbids) AS artist_mbid, {entity_mbid}"
    return f"""
        WITH exploded_mlhd_data AS (
            SELECT {explode_clause}
                 , user_id
              FROM {mlhd_table}
        ), mlhd_table AS (
            SELECT {select_clause}
                 , count(*) AS listen_count
                 , count(distinct user_id) AS user_count
              FROM exploded_mlhd_data
          GROUP BY {select_clause}
        ), exploded_listen_data AS (
            SELECT {explode_clause}
                 , user_id
              FROM {listens_table}
        ), listens_table AS (
            SELECT {select_clause}
                 , count(*) AS listen_count
                 , count(distinct user_id) AS user_count
              FROM exploded_listen_data
          GROUP BY {select_clause}
        )   SELECT {select_clause}
                 , m.listen_count + l.listen_count AS total_listen_count
                 , m.user_count + l.user_count AS total_user_count
              FROM mlhd_table m
              JOIN listens_table l
             USING ({select_clause})
    """


def main():
    """ Generate popularity data for MLHD data. """
    listens_table = "listens_popularity"
    get_listens_from_dump().createOrReplaceTempView(listens_table)

    mlhd_table = f"parquet.`{MLHD_PLUS_DATA_DIRECTORY}`"

    queries = {
        "mlhd_popularity_recording": get_popularity_query("recording", mlhd_table, listens_table),
        "mlhd_popularity_release": get_popularity_query("release", mlhd_table, listens_table),
        "mlhd_popularity_artist": get_popularity_per_artist_query("artist", mlhd_table, listens_table),
        "mlhd_popularity_top_recording": get_popularity_per_artist_query("recording", mlhd_table, listens_table),
        "mlhd_popularity_top_release": get_popularity_per_artist_query("release", mlhd_table, listens_table)
    }

    for name, query in queries.items():
        yield {"type": f"{name}_start"}
        for message in generate_popularity_stats(name, query):
            yield message
        yield {"type": f"{name}_end"}
