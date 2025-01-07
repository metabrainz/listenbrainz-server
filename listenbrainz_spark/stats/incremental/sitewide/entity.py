import logging
from abc import ABC

from listenbrainz_spark.path import LISTENBRAINZ_SITEWIDE_STATS_DIRECTORY
from listenbrainz_spark.stats.incremental import IncrementalStats

logger = logging.getLogger(__name__)


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
