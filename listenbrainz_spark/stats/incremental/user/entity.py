import abc
import json
import logging
from datetime import date
from typing import Optional, Iterator, Dict, Tuple

from more_itertools import chunked
from pydantic import ValidationError
from pyspark.sql import DataFrame

from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_group_stat import ReleaseGroupRecord
from data.model.user_release_stat import ReleaseRecord
from listenbrainz_spark.path import LISTENBRAINZ_USER_STATS_DIRECTORY
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental import IncrementalStats
from listenbrainz_spark.stats.user import USERS_PER_MESSAGE
from listenbrainz_spark.utils import read_files_from_HDFS


logger = logging.getLogger(__name__)

entity_model_map = {
    "artists": ArtistRecord,
    "releases": ReleaseRecord,
    "recordings": RecordingRecord,
    "release_groups": ReleaseGroupRecord,
}


class UserEntity(IncrementalStats, abc.ABC):

    def  __init__(self, entity: str, stats_range: str, database: Optional[str], message_type: Optional[str]):
        super().__init__(entity, stats_range)
        if database:
            self.database = database
        else:
            self.database = f"{self.entity}_{self.stats_range}_{date.today().strftime('%Y%m%d')}"
        self.message_type = message_type

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

    def generate_stats(self, top_entity_limit: int) -> Tuple[bool, DataFrame]:
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
        return only_inc_users, results_df

    def parse_one_user_stats(self, entry: dict):
        count_key = self.entity + "_count"
        total_entity_count = entry[count_key]

        entity_list = []
        for item in entry[self.entity]:
            try:
                entity_model_map[self.entity](**item)
                entity_list.append(item)
            except ValidationError:
                logger.error("Invalid entry in entity stats:", exc_info=True)
                total_entity_count -= 1

        return {
            "user_id": entry["user_id"],
            "data": entity_list,
            "count": total_entity_count
        }

    def create_messages(self, only_inc_users, results: DataFrame) -> Iterator[Dict]:
        """
        Create messages to send the data to the webserver via RabbitMQ

        Args:
            only_inc_users: whether stats were generated only for users with listens present in incremental dumps
            results: Data to sent to the webserver
        """
        if not only_inc_users:
            yield {
                "type": "couchdb_data_start",
                "database": self.database
            }

        from_ts = int(self.from_date.timestamp())
        to_ts = int(self.to_date.timestamp())

        data = results.toLocalIterator()
        for entries in chunked(data, USERS_PER_MESSAGE):
            multiple_user_stats = []
            for entry in entries:
                row = entry.asDict(recursive=True)
                processed_stat = self.parse_one_user_stats(row)
                if processed_stat is not None:
                    multiple_user_stats.append(processed_stat)

            yield {
                "type": self.message_type,
                "stats_range": self.stats_range,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "entity": self.entity,
                "data": multiple_user_stats,
                "database": self.database
            }

        if not only_inc_users:
            yield {
                "type": "couchdb_data_end",
                "database": self.database
            }

    def main(self, top_entity_limit: int):
        only_inc_users, results = self.generate_stats(top_entity_limit)
        itr = self.create_messages(only_inc_users, results)
        return itr
