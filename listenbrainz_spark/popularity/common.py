from typing import Iterator, Dict

from more_itertools import chunked
from pyspark.sql import DataFrame
from typing import Optional

from listenbrainz_spark.stats.incremental.message_creator import MessageCreator

ROWS_PER_MESSAGE = 10000


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


class PopularityMessageCreator(MessageCreator):

    def __init__(self, entity: str, message_type: str, is_mlhd: bool):
        super().__init__(entity, message_type)
        self.is_mlhd = is_mlhd

    def create_start_message(self):
        yield {"is_mlhd": self.is_mlhd, "entity": self.entity, "message_type": self.message_type + "_start"}

    def create_end_message(self):
        yield {"is_mlhd": self.is_mlhd, "entity": self.entity, "message_type": self.message_type + "_end"}

    def parse_row(self, row: Dict) -> Optional[Dict]:
        return row

    def create_messages(self, results: DataFrame) -> Iterator[Dict]:
        itr = results.toLocalIterator()
        for chunk in chunked(itr, ROWS_PER_MESSAGE):
            multiple_stats = [row.asDict(recursive=True) for row in chunk]
            yield {
                "type": self.message_type,
                "is_mlhd": self.is_mlhd,
                "entity": self.entity,
                "data": multiple_stats,
            }
