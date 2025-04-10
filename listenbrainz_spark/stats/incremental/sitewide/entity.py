import abc
import logging
from datetime import datetime
from typing import Iterator, Dict, Optional, List

from pydantic import ValidationError
from pyspark.sql import DataFrame

from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_group_stat import ReleaseGroupRecord
from data.model.user_release_stat import ReleaseRecord
from listenbrainz_spark.path import LISTENBRAINZ_SITEWIDE_STATS_DIRECTORY

from listenbrainz_spark.stats.incremental.message_creator import SitewideStatsMessageCreator
from listenbrainz_spark.stats.incremental.query_provider import QueryProvider
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector

logger = logging.getLogger(__name__)

entity_model_map = {
    "artists": ArtistRecord,
    "releases": ReleaseRecord,
    "recordings": RecordingRecord,
    "release_groups": ReleaseGroupRecord,
}


class SitewideStatsQueryProvider(QueryProvider, abc.ABC):
    """ See base class QueryProvider for details. """

    def get_base_path(self) -> str:
        return LISTENBRAINZ_SITEWIDE_STATS_DIRECTORY

    def get_table_prefix(self) -> str:
        return f"sitewide_{self.entity}_{self.stats_range}"

    def get_filter_aggregate_query(self, existing_aggregate: str, incremental_aggregate: str,
                                   existed_created: Optional[datetime]) -> str:
        return f"SELECT * FROM {existing_aggregate}"


class SitewideEntityStatsQueryProvider(SitewideStatsQueryProvider, abc.ABC):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector, top_entity_limit: int):
        super().__init__(selector)
        self.top_entity_limit = top_entity_limit

    def get_listen_count_limit(self) -> int:
        """ Return the per user per entity listen count above which it should
        be capped. The rationale is to avoid a single user's listens from
        over-influencing the sitewide stats.

        For instance: if the limit for yearly recordings count is 500 and a user
        listens to a particular recording for 10000 times, it will be counted as
        500 for calculating the stat.
        """
        return 500


class SitewideEntityStatsMessageCreator(SitewideStatsMessageCreator):

    def __init__(self, entity, selector):
        super().__init__(entity, "sitewide_entity", selector)

    def create_messages(self, results: DataFrame, only_inc: bool) -> Iterator[Dict]:
        message = {
            "type": self.message_type,
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
