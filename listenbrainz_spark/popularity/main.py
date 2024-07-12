from more_itertools import chunked

from listenbrainz_spark import config
from listenbrainz_spark.path import MLHD_PLUS_DATA_DIRECTORY, RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_dump, read_files_from_HDFS

STATS_PER_MESSAGE = 10000


def generate_popularity_stats(name, query, mlhd):
    """ Execute the given query and generate statistics. """
    df = run_query(query)
    df\
        .write\
        .format("parquet")\
        .save(config.HDFS_CLUSTER_URI + "/" + name, mode="overwrite")

    itr = df.toLocalIterator()

    for rows in chunked(itr, STATS_PER_MESSAGE):
        entries = []
        for row in rows:
            entry = row.asDict(recursive=True)
            entries.append(entry)

        yield {
            "type": name,
            "data": entries,
            "mlhd": mlhd
        }


def get_release_group_popularity_query(table, rel_cache_table):
    """ Get the query to generate release group popularity stats using both MLHD+ and listens data """
    return f"""
        SELECT rel.release_group_mbid
             , count(*) AS total_listen_count
             , count(DISTINCT user_id) AS total_user_count
          FROM {table} t
          JOIN {rel_cache_table} rel
            ON t.release_mbid = rel.release_mbid
           AND rel.release_group_mbid != ""
      GROUP BY rel.release_group_mbid
    """


def get_release_group_popularity_per_artist_query(table, rel_cache_table):
    """ Get the query to generate release group popularity per artists stats using both MLHD+ and listens data """
    return f"""
        WITH intermediate AS (
            SELECT explode(artist_credit_mbids) AS artist_mbid
                 , release_mbid
                 , user_id
              FROM {table}
        )   SELECT artist_mbid
                 , rel.release_group_mbid
                 , count(*) AS total_listen_count
                 , count(DISTINCT user_id) AS total_user_count
              FROM intermediate i
              JOIN {rel_cache_table} rel
                ON i.release_mbid = rel.release_mbid
             WHERE artist_mbid IS NOT NULL
               AND rel.release_group_mbid != ""
          GROUP BY artist_mbid
                 , rel.release_group_mbid
    """


def get_popularity_query(entity, table):
    """ Get the query to generate popularity stats for the given entity using both MLHD+ and listens data """
    entity_mbid = f"{entity}_mbid"
    return f"""
        SELECT {entity_mbid}
             , count(*) AS total_listen_count
             , count(DISTINCT user_id) AS total_user_count
          FROM {table}
         WHERE {entity_mbid} IS NOT NULL
           AND {entity_mbid} != ""
      GROUP BY {entity_mbid}
    """


def get_popularity_per_artist_query(entity, table):
    """ Get the query to generate top popular entities per artists stats from MLHD+ and listens data """
    if entity == "artist":
        select_clause = "artist_mbid"
        explode_clause = "explode(artist_credit_mbids) AS artist_mbid"
        where_clause = "artist_mbid IS NOT NULL"
    else:
        entity_mbid = f"{entity}_mbid"
        select_clause = f"artist_mbid, {entity_mbid}"
        explode_clause = f"explode(artist_credit_mbids) AS artist_mbid, {entity_mbid}"
        where_clause = f"artist_mbid IS NOT NULL AND {entity_mbid} IS NOT NULL AND {entity_mbid} != ''"
    return f"""
        WITH intermediate AS (
            SELECT {explode_clause}
                 , user_id
              FROM {table}
        )   SELECT {select_clause}
                 , count(*) AS total_listen_count
                 , count(DISTINCT user_id) AS total_user_count
              FROM intermediate
             WHERE {where_clause}
          GROUP BY {select_clause}
    """


def main(mlhd):
    """ Generate popularity data for MLHD data. """
    if mlhd:
        table = f"parquet.`{MLHD_PLUS_DATA_DIRECTORY}`"
    else:
        table = "listens_popularity"
        get_listens_from_dump().createOrReplaceTempView(table)

    rel_cache_table = "release_data_cache"
    read_files_from_HDFS(RELEASE_METADATA_CACHE_DATAFRAME).createOrReplaceTempView(rel_cache_table)

    queries = {
        "popularity_top_recording": get_popularity_per_artist_query("recording", table),
        "popularity_recording": get_popularity_query("recording", table),
        "popularity_release": get_popularity_query("release", table),
        "popularity_release_group": get_release_group_popularity_query(table, rel_cache_table),
        "popularity_top_release_group": get_release_group_popularity_per_artist_query(table, rel_cache_table),
        "popularity_artist": get_popularity_per_artist_query("artist", table),
        "popularity_top_release": get_popularity_per_artist_query("release", table)
    }

    for name, query in queries.items():
        if mlhd:
            name = "mlhd_" + name

        yield {"type": f"{name}_start"}
        for message in generate_popularity_stats(name, query, mlhd):
            yield message
        yield {"type": f"{name}_end"}
