import json
import logging
from datetime import datetime, date
from typing import Iterator, Optional, Dict

from more_itertools import chunked
from pydantic import ValidationError

from data.model.common_stat_spark import UserStatRecords, StatMessage
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.common.listening_activity import setup_time_range
from listenbrainz_spark.stats.incremental.user.listening_activity import ListeningActivityUserEntity
from listenbrainz_spark.stats.user import USERS_PER_MESSAGE
from listenbrainz_spark.utils import get_listens_from_dump


logger = logging.getLogger(__name__)

def get_listening_activity(stats_range: str, message_type="user_listening_activity", database: str = None)\
        -> Iterator[Optional[Dict]]:
    """ Compute the number of listens for a time range compared to the previous range

    Given a time range, this computes a histogram of a users' listens for that range
    and the previous range of the same duration, so that they can be compared. The
    bin size of the histogram depends on the size of the range (e.g.
    year -> 12 months, month -> ~30 days, week -> ~7 days, see get_time_range for
    details). These values are used on the listening activity reports.
    """
    logger.debug(f"Calculating listening_activity_{stats_range}")
    entity_obj = ListeningActivityUserEntity(stats_range, database, message_type)
    return entity_obj.main(0)
