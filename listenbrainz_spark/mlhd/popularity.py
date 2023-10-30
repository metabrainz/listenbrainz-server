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
        WITH intermediate AS (
            SELECT {entity_mbid}
                 , user_id
              FROM {mlhd_table}
             UNION ALL
            SELECT {entity_mbid}
                 , user_id
              FROM {listens_table}
        )   SELECT {entity_mbid}
                 , count(*) AS total_listen_count
                 , count(distinct user_id) AS total_user_count
              FROM intermediate
             WHERE {entity_mbid} IS NOT NULL
          GROUP BY {entity_mbid}
    """


def get_popularity_per_artist_query(entity, mlhd_table, listens_table):
    """ Get the query to generate top popular entities per artists stats from MLHD+ and listens data """
    if entity == "artist":
        select_clause = "artist_mbid"
        explode_clause = "explode(artist_credit_mbids) AS artist_mbid"
        where_clause = "artist_mbid IS NOT NULL"
    else:
        entity_mbid = f"{entity}_mbid"
        select_clause = f"artist_mbid, {entity_mbid}"
        explode_clause = f"explode(artist_credit_mbids) AS artist_mbid, {entity_mbid}"
        where_clause = f"artist_mbid IS NOT NULL AND {entity_mbid} IS NOT NULL"
    return f"""
        WITH intermediate AS (
            SELECT {explode_clause}
                 , user_id
              FROM {mlhd_table}
             UNION ALL
            SELECT {explode_clause}
                 , user_id
              FROM {listens_table}
        )   SELECT {select_clause}
                 , count(*) AS total_listen_count
                 , count(distinct user_id) AS total_user_count
              FROM intermediate
             WHERE {where_clause}
          GROUP BY {select_clause}
    """


def main():
    """ Generate popularity data for MLHD data. """
    listens_table = "listens_popularity"
    get_listens_from_dump().createOrReplaceTempView(listens_table)

    mlhd_table = f"parquet.`{MLHD_PLUS_DATA_DIRECTORY}`"

    queries = {
        "mlhd_popularity_top_recording": get_popularity_per_artist_query("recording", mlhd_table, listens_table),
        "mlhd_popularity_recording": get_popularity_query("recording", mlhd_table, listens_table),
        "mlhd_popularity_release": get_popularity_query("release", mlhd_table, listens_table),
        "mlhd_popularity_artist": get_popularity_per_artist_query("artist", mlhd_table, listens_table),
        "mlhd_popularity_top_release": get_popularity_per_artist_query("release", mlhd_table, listens_table)
    }

    for name, query in queries.items():
        yield {"type": f"{name}_start"}
        for message in generate_popularity_stats(name, query):
            yield message
        yield {"type": f"{name}_end"}
