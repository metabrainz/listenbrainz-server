import logging
import os.path
from datetime import datetime
from typing import Iterator, Optional, Dict

from more_itertools import chunked

from listenbrainz_spark.path import LISTENBRAINZ_EXPERIMENTAL_STATS_DIR
from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.stats.incremental.artist import Artist
from listenbrainz_spark.stats.incremental.job import get_job
from listenbrainz_spark.stats.incremental.recording import Recording
from listenbrainz_spark.stats.incremental.release import Release
from listenbrainz_spark.stats.incremental.release_group import ReleaseGroup
from listenbrainz_spark.stats.user import USERS_PER_MESSAGE
from listenbrainz_spark.utils import read_files_from_HDFS

logger = logging.getLogger(__name__)


entity_map = {
    "artists": Artist(),
    "recordings": Recording(),
    "releases": Release(),
    "release_groups": ReleaseGroup(),
}


def create_messages(data, entity: str, stats_range: str, from_date: datetime, to_date: datetime,
                    message_type: str, is_full: bool, database: str) \
        -> Iterator[Optional[Dict]]:
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data: Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_date: The start time of the stats
        to_date: The end time of the stats
        message_type: used to decide which handler on LB webserver side should
            handle this message. can be "user_entity" or "year_in_music_top_stats"
        database: the name of the database in which the webserver should store the data

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    if database is None:
        database = f"{entity}_{stats_range}"

    if is_full:
        yield {
            "type": "couchdb_data_start",
            "database": database
        }

    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entries in chunked(data, USERS_PER_MESSAGE):
        multiple_user_stats = []
        for entry in entries:
            multiple_user_stats.append(entry.asDict(recursive=True))

        yield {
            "type": message_type,
            "stats_range": stats_range,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "entity": entity,
            "data": multiple_user_stats,
            "database": database
        }

    if is_full:
        yield {
            "type": "couchdb_data_end",
            "database": database
        }


def get_entity_stats(entity: str, stats_range: str, database: str):
    message_type = "user_entity"
    from_date, to_date = get_dates_for_stats_range(stats_range)
    previous_job = get_job(message_type, entity, stats_range)
    is_full = previous_job is None or previous_job["latest_created_at"] <= from_date

    entity_obj = entity_map.get(entity)

    cache_tables = []
    for idx, df_path in enumerate(entity_obj.get_cache_tables()):
        df_name = f"entity_data_cache_{idx}"
        cache_tables.append(df_name)
        read_files_from_HDFS(df_path).createOrReplaceTempView(df_name)

    stats_aggregation_path = os.path.join(LISTENBRAINZ_EXPERIMENTAL_STATS_DIR, message_type, entity, stats_range)

    if is_full:
        top_entity_df = entity_obj.process_full(from_date, to_date, message_type, entity, stats_range, stats_aggregation_path)
        combined_entity_table = None
    else:
        previous_created_at = previous_job["latest_created_at"]
        combined_entity_table = f"{entity}_{stats_range}_combined"
        top_entity_df = entity_obj.process_incremental(
            from_date, to_date, previous_created_at, message_type,
            entity, stats_range, stats_aggregation_path, combined_entity_table
        )

    top_entity = top_entity_df.toLocalIterator()

    messages = create_messages(top_entity, entity, stats_range, from_date, to_date, message_type, is_full, database)
    for message in messages:
        yield message

    if not is_full:
        entity_obj.post_process_incremental(message_type, entity, stats_range, combined_entity_table, stats_aggregation_path)
