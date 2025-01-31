from typing import List

from listenbrainz_spark.path import LISTENBRAINZ_POPULARITY_DIRECTORY, RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.popularity.common import get_popularity_per_artist_query, \
    get_release_group_popularity_per_artist_query, get_popularity_query
from listenbrainz_spark.stats.incremental.query_provider import QueryProvider
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector


class PopularityProvider(QueryProvider):

    def __init__(self, selector: ListenRangeSelector, entity: str):
        super().__init__(selector)
        self._entity = entity

    @property
    def entity(self):
        return self._entity

    def get_table_prefix(self) -> str:
        return f"popularity_{self.entity}_{self.stats_range}"

    def get_base_path(self) -> str:
        return LISTENBRAINZ_POPULARITY_DIRECTORY

    def get_filter_aggregate_query(self, existing_aggregate: str, incremental_aggregate: str) -> str:
        entity_id = self.get_entity_id()
        return f"""
            WITH incremental_users AS (
                SELECT DISTINCT {entity_id} FROM {incremental_aggregate}
            )
            SELECT *
              FROM {existing_aggregate} ea
             WHERE EXISTS(SELECT 1 FROM incremental_users iu WHERE iu.{entity_id} = ea.{entity_id})
        """

    def get_cache_tables(self) -> List[str]:
        if self.entity == "release_group":
            return [RELEASE_METADATA_CACHE_DATAFRAME]
        return []

    def get_entity_id(self):
        return self.entity + "_mbid"

    def get_aggregate_query(self, table: str, cache_tables: List[str]) -> str:
        if self.entity == "artist":
            return get_popularity_per_artist_query("artist", table)
        elif self.entity == "release_group":
            return get_release_group_popularity_per_artist_query(table, cache_tables[0])
        else:
            return get_popularity_query(self.entity, table)

    def get_stats_query(self, final_aggregate: str) -> str:
        return f"SELECT * FROM {final_aggregate}"

    def get_combine_aggregates_query(self, existing_aggregate: str, incremental_aggregate: str) -> str:
        entity_mbid = self.get_entity_id()
        return f"""
          WITH intermediate_table AS (
            SELECT {entity_mbid}
                 , total_listen_count
                 , total_user_count
              FROM {existing_aggregate}
             UNION ALL
            SELECT {entity_mbid}
                 , total_listen_count
                 , total_user_count
              FROM {incremental_aggregate}
          )
            SELECT {entity_mbid}
                 , SUM(total_listen_count) AS total_listen_count
                 , SUM(total_user_count) AS total_user_count
              FROM intermediate_table
          GROUP BY {entity_mbid}
        """


class TopPerArtistPopularityProvider(QueryProvider):

    def __init__(self, selector: ListenRangeSelector, entity: str):
        super().__init__(selector)
        self._entity = entity

    @property
    def entity(self):
        return self._entity

    def get_table_prefix(self) -> str:
        return f"popularity_top_per_artist_{self.entity}_{self.stats_range}"

    def get_base_path(self) -> str:
        return LISTENBRAINZ_POPULARITY_DIRECTORY

    def get_filter_aggregate_query(self, existing_aggregate: str, incremental_aggregate: str) -> str:
        entity_id = self.get_entity_id()
        return f"""
            WITH incremental_artists AS (
                SELECT DISTINCT artist_mbid, {entity_id} FROM {incremental_aggregate}
            )
            SELECT *
              FROM {existing_aggregate} ea
             WHERE EXISTS(SELECT 1
                            FROM incremental_artists iu
                           WHERE iu.{entity_id} = ea.{entity_id}
                             AND iu.artist_mbid = ea.artist_mbid
             )
        """

    def get_cache_tables(self) -> List[str]:
        if self.entity == "release_group":
            return [RELEASE_METADATA_CACHE_DATAFRAME]
        return []

    def get_entity_id(self):
        return self.entity + "_mbid"

    def get_aggregate_query(self, table: str, cache_tables: List[str]) -> str:
        if self.entity == "release_group":
            return get_release_group_popularity_per_artist_query(table, cache_tables[0])
        return get_popularity_per_artist_query(self.entity, table)

    def get_stats_query(self, final_aggregate: str) -> str:
        return f"SELECT * FROM {final_aggregate}"

    def get_combine_aggregates_query(self, existing_aggregate: str, incremental_aggregate: str) -> str:
        entity_mbid = self.get_entity_id()
        return f"""
          WITH intermediate_table AS (
            SELECT artist_mbid
                 , {entity_mbid}
                 , total_listen_count
                 , total_user_count
              FROM {existing_aggregate}
             UNION ALL
            SELECT artist_mbid
                 , {entity_mbid}
                 , total_listen_count
                 , total_user_count
              FROM {incremental_aggregate}
          )
            SELECT artist_mbid
                 , {entity_mbid}
                 , SUM(total_listen_count) AS total_listen_count
                 , SUM(total_user_count) AS total_user_count
              FROM intermediate_table
          GROUP BY artist_mbid
                 , {entity_mbid}
        """
