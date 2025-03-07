import abc
import logging
from typing import Iterator, Dict

from more_itertools import chunked
from pydantic import ValidationError
from pyspark.sql import DataFrame

from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_group_stat import ReleaseGroupRecord
from data.model.user_release_stat import ReleaseRecord
from listenbrainz_spark.path import LISTENBRAINZ_USER_STATS_DIRECTORY
from listenbrainz_spark.listens.cache import get_incremental_users_df
from listenbrainz_spark.stats.incremental.message_creator import StatsMessageCreator
from listenbrainz_spark.stats.incremental.query_provider import QueryProvider
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector

logger = logging.getLogger(__name__)

entity_model_map = {
    "artists": ArtistRecord,
    "releases": ReleaseRecord,
    "recordings": RecordingRecord,
    "release_groups": ReleaseGroupRecord,
}


class UserStatsQueryProvider(QueryProvider, abc.ABC):
    """ See base class QueryProvider for details. """

    def get_base_path(self) -> str:
        return LISTENBRAINZ_USER_STATS_DIRECTORY

    def get_table_prefix(self) -> str:
        return f"user_{self.entity}_{self.stats_range}"

    def get_filter_aggregate_query(self, aggregate, inc_listens_table, existing_created):
        """ Filter listens from existing aggregate to only include listens for entities having listens in the
        incremental dumps.
        """
        inc_users_df = get_incremental_users_df()
        inc_users_df.createOrReplaceTempView("inc_users_table")
        return f"""
              WITH incremental_users AS (
            SELECT user_id
              FROM inc_users_table
             WHERE created >= to_timestamp('{existing_created}')
            )
            SELECT *
              FROM {aggregate} ea
             WHERE EXISTS(SELECT 1 FROM incremental_users iu WHERE iu.user_id = ea.user_id)
        """


class UserEntityStatsQueryProvider(UserStatsQueryProvider, abc.ABC):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector, top_entity_limit: int):
        super().__init__(selector)
        self.top_entity_limit = top_entity_limit


class UserStatsMessageCreator(StatsMessageCreator, abc.ABC):

    def items_per_message(self):
        """ Get the number of items to chunk per message """
        return 25

    def create_messages(self, results: DataFrame, only_inc: bool) -> Iterator[Dict]:
        from_ts = int(self.from_date.timestamp())
        to_ts = int(self.to_date.timestamp())

        data = results.toLocalIterator()
        for entries in chunked(data, self.items_per_message()):
            multiple_rows = []
            for entry in entries:
                processed_row = entry.asDict(recursive=True)
                processed_stat = self.parse_row(processed_row)
                if processed_stat is not None:
                    multiple_rows.append(processed_stat)

            message = {
                "type": self.message_type,
                "stats_range": self.stats_range,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "entity": self.entity,
                "data": multiple_rows,
            }
            if self.database:
                message["database"] = self.database
            elif only_inc:
                message["database_prefix"] = self.default_database_prefix
            else:
                message["database"] = self.default_database
            yield message


class UserEntityStatsMessageCreator(UserStatsMessageCreator):

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def parse_row(self, row):
        count_key = self.entity + "_count"
        total_entity_count = row[count_key]

        entity_list = []
        for item in row[self.entity]:
            try:
                entity_model_map[self.entity](**item)
                entity_list.append(item)
            except ValidationError:
                logger.error("Invalid entry in entity stats:", exc_info=True)
                total_entity_count -= 1

        return {
            "user_id": row["user_id"],
            "data": entity_list,
            "count": total_entity_count
        }
