import abc

from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.job import start_job, save_parquet, end_job
from listenbrainz_spark.utils import get_listens_from_dump, read_files_from_HDFS


class Entity(abc.ABC):

    @abc.abstractmethod
    def get_cache_tables(self):
        pass

    @abc.abstractmethod
    def get_stats_from_listens(self, listen_table: str):
        pass

    @abc.abstractmethod
    def combine_existing_and_new_stats(self, existing_table: str, new_table: str):
        pass

    @abc.abstractmethod
    def filter_top_full(self, table: str, k: int):
        pass

    @abc.abstractmethod
    def filter_top_incremental(self, incremental_listens_table: str, combined_stats_table: str, k: int):
        pass

    def process_full(self, from_date, to_date, type_, entity, stats_range, stats_aggregation_path):
        full_listens_table = f"user_{entity}_{stats_range}_full"
        get_listens_from_dump(from_date, to_date).createOrReplaceTempView(full_listens_table)
        latest_created_at = run_query(f"select max(created) as latest_created_at from {full_listens_table}") \
            .collect()[0].latest_created_at
        start_job(type_, entity, stats_range, latest_created_at)

        full_entity_df = self.get_stats_from_listens(full_listens_table)
        save_parquet(full_entity_df, stats_aggregation_path)

        end_job(type_, entity, stats_range)

        entity_table = f"{entity}_{stats_range}_full"
        full_entity_df.createOrReplaceTempView(entity_table)

        return self.filter_top_full(entity_table, 1000)

    def process_incremental(self, from_date, to_date, previous_created_at, type_, entity,
                            stats_range, stats_aggregation_path, combined_stats_table):
        existing_entity_table = f"{entity}_{stats_range}_existing"
        read_files_from_HDFS(stats_aggregation_path).createOrReplaceTempView(existing_entity_table)

        incremental_listens_table = f"user_{entity}_{stats_range}_new"
        read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH) \
            .filter(f"created > to_timestamp('{previous_created_at}')") \
            .filter(f"listened_at >= to_timestamp('{from_date}')") \
            .filter(f"listened_at <= to_timestamp('{to_date}')") \
            .createOrReplaceTempView(incremental_listens_table)

        new_row_df = run_query(f"select max(created) as latest_created_at from {incremental_listens_table}") \
            .collect()[0]
        latest_created_at = new_row_df.latest_created_at or previous_created_at
        start_job(type_, entity, stats_range, latest_created_at)

        new_entity_df = self.get_stats_from_listens(incremental_listens_table)
        new_entity_table = f"{entity}_{stats_range}_new"
        new_entity_df.createOrReplaceTempView(new_entity_table)

        combined_entity_df = self.combine_existing_and_new_stats(existing_entity_table, new_entity_table)
        combined_entity_df.createOrReplaceTempView(combined_stats_table)

        return self.filter_top_incremental(incremental_listens_table, combined_stats_table,1000)

    def post_process_incremental(self, type_, entity, stats_range, combined_artists_table, stats_aggregation_path):
        new_stats_df = run_query(f"""
            SELECT user_id
                 , artist_mbid
                 , artist_name
                 , new_listen_count AS listen_count
              FROM {combined_artists_table}
        """)
        save_parquet(new_stats_df, stats_aggregation_path)
        end_job(type_, entity, stats_range)
