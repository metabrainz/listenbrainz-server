import abc
import logging

from listenbrainz_spark.path import LISTENBRAINZ_USER_STATS_DIRECTORY
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental import IncrementalStats
from listenbrainz_spark.utils import read_files_from_HDFS


logger = logging.getLogger(__name__)


class UserEntity(IncrementalStats, abc.ABC):

    def get_base_path(self) -> str:
        return LISTENBRAINZ_USER_STATS_DIRECTORY

    def get_table_prefix(self) -> str:
        return f"user_{self.entity}_{self.stats_range}"

    def filter_existing_aggregate(self, existing_aggregate, incremental_aggregate):
        query = f"""
            WITH incremental_users AS (
                SELECT DISTINCT user_id FROM {incremental_aggregate}
            )
            SELECT *
              FROM {existing_aggregate} ea
             WHERE EXISTS(SELECT 1 FROM incremental_users iu WHERE iu.user_id = ea.user_id)
        """
        return run_query(query)

    def generate_stats(self, top_entity_limit: int):
        self.setup_cache_tables()
        prefix = self.get_table_prefix()

        if not self.partial_aggregate_usable():
            self.create_partial_aggregate()
            only_inc_users = False
        else:
            only_inc_users = True

        partial_df = read_files_from_HDFS(self.get_existing_aggregate_path())
        partial_table = f"{prefix}_existing_aggregate"
        partial_df.createOrReplaceTempView(partial_table)

        if self.incremental_dump_exists():
            inc_df = self.create_incremental_aggregate()
            inc_table = f"{prefix}_incremental_aggregate"
            inc_df.createOrReplaceTempView(inc_table)

            if only_inc_users:
                filtered_aggregate_df = self.filter_existing_aggregate(partial_table, inc_table)
                filtered_table = f"{prefix}_filtered_aggregate"
                filtered_aggregate_df.createOrReplaceTempView(filtered_table)
            else:
                filtered_table = partial_table

            final_df = self.combine_aggregates(filtered_table, inc_table)
        else:
            final_df = partial_df
            only_inc_users = False

        final_table = f"{prefix}_final_aggregate"
        final_df.createOrReplaceTempView(final_table)

        results_df = self.get_top_n(final_table, top_entity_limit)
        return self.from_date, self.to_date, only_inc_users, results_df.toLocalIterator()
