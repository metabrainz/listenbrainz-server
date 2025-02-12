import abc
import logging

from listenbrainz_spark.path import LISTENBRAINZ_LISTENER_STATS_DIRECTORY
from listenbrainz_spark.stats.incremental.query_provider import QueryProvider
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserStatsMessageCreator

logger = logging.getLogger(__name__)


class EntityListenerStatsQueryProvider(QueryProvider, abc.ABC):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector, top_entity_limit: int):
        super().__init__(selector)
        self.top_entity_limit = top_entity_limit

    def get_table_prefix(self) -> str:
        return f"{self.entity}_listeners_{self.stats_range}"

    def get_base_path(self) -> str:
        return LISTENBRAINZ_LISTENER_STATS_DIRECTORY


class EntityListenerStatsMessageCreator(UserStatsMessageCreator):

    def items_per_message(self):
        return 10000

    @property
    def default_database_prefix(self):
        return f"{self.entity}_listeners_{self.stats_range}"
