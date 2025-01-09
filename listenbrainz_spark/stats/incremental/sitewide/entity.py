import logging
from abc import ABC
from typing import Iterator, Dict

from pydantic import ValidationError
from pyspark.sql import DataFrame

from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_group_stat import ReleaseGroupRecord
from data.model.user_release_stat import ReleaseRecord
from listenbrainz_spark.path import LISTENBRAINZ_SITEWIDE_STATS_DIRECTORY
from listenbrainz_spark.stats import SITEWIDE_STATS_ENTITY_LIMIT
from listenbrainz_spark.stats.incremental import IncrementalStats
from listenbrainz_spark.utils import read_files_from_HDFS

logger = logging.getLogger(__name__)

entity_model_map = {
    "artists": ArtistRecord,
    "releases": ReleaseRecord,
    "recordings": RecordingRecord,
    "release_groups": ReleaseGroupRecord,
}


class SitewideEntity(IncrementalStats, ABC):

    def get_base_path(self) -> str:
        return LISTENBRAINZ_SITEWIDE_STATS_DIRECTORY

    def get_table_prefix(self) -> str:
        return f"sitewide_{self.entity}_{self.stats_range}"

    def get_listen_count_limit(self) -> int:
        """ Return the per user per entity listen count above which it should
        be capped. The rationale is to avoid a single user's listens from
        over-influencing the sitewide stats.

        For instance: if the limit for yearly recordings count is 500 and a user
        listens to a particular recording for 10000 times, it will be counted as
        500 for calculating the stat.
        """
        return 500

    def generate_stats(self, top_entity_limit: int) -> DataFrame:
        """
        Generate statistics of the given type, entity and stats range.

        Args:
            top_entity_limit (int): The maximum number of top entities to retrieve.

        Returns a DataFrame of the results.
        """
        self.setup_cache_tables()
        prefix = self.get_table_prefix()

        if not self.partial_aggregate_usable():
            self.create_partial_aggregate()
        partial_df = read_files_from_HDFS(self.get_existing_aggregate_path())
        partial_table = f"{prefix}_existing_aggregate"
        partial_df.createOrReplaceTempView(partial_table)

        if self.incremental_dump_exists():
            inc_df = self.create_incremental_aggregate()
            inc_table = f"{prefix}_incremental_aggregate"
            inc_df.createOrReplaceTempView(inc_table)
            final_df = self.combine_aggregates(partial_table, inc_table)
        else:
            final_df = partial_df

        final_table = f"{prefix}_final_aggregate"
        final_df.createOrReplaceTempView(final_table)

        return self.get_top_n(final_table, top_entity_limit)

    def create_messages(self, results: DataFrame) -> Iterator[Dict]:
        """
        Create messages to send the data to the webserver via RabbitMQ

        Args:
            results: Data to sent to the webserver

        Returns:
            messages: A list of messages to be sent via RabbitMQ
        """
        message = {
            "type": "sitewide_entity",
            "stats_range": self.stats_range,
            "from_ts": int(self.from_date.timestamp()),
            "to_ts": int(self.to_date.timestamp()),
            "entity": self.entity,
        }
        entry = results.collect()[0].asDict(recursive=True)
        stats = entry["stats"]
        count = entry["total_count"]

        entity_list = []
        for item in stats:
            try:
                entity_model_map[self.entity](**item)
                entity_list.append(item)
            except ValidationError:
                logger.error("Invalid entry in entity stats", exc_info=True)
                count -= 1

        message["count"] = count
        message["data"] = entity_list

        yield message

    def main(self):
        results = self.generate_stats(SITEWIDE_STATS_ENTITY_LIMIT)
        return self.create_messages(results)
