import abc
import logging
from datetime import date
from typing import Optional

from listenbrainz_spark.path import LISTENBRAINZ_LISTENER_STATS_DIRECTORY
from listenbrainz_spark.stats.incremental.user.entity import UserEntity

logger = logging.getLogger(__name__)


class EntityListener(UserEntity, abc.ABC):

    def __init__(self, entity: str, stats_range: str, database: Optional[str], message_type: Optional[str]):
        if not database:
            database = f"{entity}_listeners_{stats_range}_{date.today().strftime('%Y%m%d')}"
        super().__init__(entity, stats_range, database, message_type)

    def get_table_prefix(self) -> str:
        return f"{self.entity}_listener_{self.stats_range}"

    def get_base_path(self) -> str:
        return LISTENBRAINZ_LISTENER_STATS_DIRECTORY

    def get_entity_id(self):
        raise NotImplementedError()

    def items_per_message(self):
        return 10000

    def parse_one_user_stats(self, entry: dict):
        return entry
