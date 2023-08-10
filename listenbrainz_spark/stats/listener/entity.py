import json
import logging
from datetime import datetime
from typing import Iterator, Optional, Dict, List

from more_itertools import chunked
from pydantic import ValidationError

from data.model.entity_listener_stat import EntityListenerRecord, ArtistListenerRecord, EntityListenerStatMessage, \
    ReleaseGroupListenerRecord
from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME, ARTIST_COUNTRY_CODE_DATAFRAME, \
    RELEASE_GROUP_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.stats.listener import artist, release_group
from listenbrainz_spark.utils import get_listens_from_dump, read_files_from_HDFS

logger = logging.getLogger(__name__)

entity_handler_map = {
    "artists": artist.get_listeners,
    "release_groups": release_group.get_listeners,
}

entity_model_map = {
    "artists": ArtistListenerRecord,
    "release_groups": ReleaseGroupListenerRecord,
}

entity_cache_map = {
    "artists": [ARTIST_COUNTRY_CODE_DATAFRAME],
    "release_groups": [RELEASE_METADATA_CACHE_DATAFRAME, RELEASE_GROUP_METADATA_CACHE_DATAFRAME],
}

ENTITIES_PER_MESSAGE = 10000  # number of entities per message
NUMBER_OF_TOP_LISTENERS = 10  # number of top listeners to retain for user stats


def get_listener_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top listeners for all entity for specified stats_range """
    logger.debug(f"Calculating {entity}_listeners_{stats_range}...")

    from_date, to_date = get_dates_for_stats_range(stats_range)
    listens_df = get_listens_from_dump(from_date, to_date)
    table = f"{entity}_listeners_{stats_range}"
    listens_df.createOrReplaceTempView(table)

    cache_dfs = []
    for idx, df_path in enumerate(entity_cache_map.get(entity)):
        df_name = f"entity_data_cache_{idx}"
        cache_dfs.append(df_name)
        read_files_from_HDFS(df_path).createOrReplaceTempView(df_name)

    messages = calculate_entity_stats(
        from_date, to_date, table, cache_dfs, entity, stats_range, database
    )

    logger.debug("Done!")

    return messages


def calculate_entity_stats(from_date: datetime, to_date: datetime, table: str, cache_tables: List[str],
                           entity: str, stats_range: str, database: str = None):
    handler = entity_handler_map[entity]
    data = handler(table, cache_tables, NUMBER_OF_TOP_LISTENERS)
    return create_messages(data=data, entity=entity, stats_range=stats_range, from_date=from_date,
                           to_date=to_date, database=database)


def parse_one_entity_stats(entry, entity: str, stats_range: str) \
        -> Optional[EntityListenerRecord]:
    try:
        data = entry.asDict(recursive=True)
        return entity_model_map[entity](**data)
    except ValidationError:
        logger.error(f"""ValidationError while calculating {stats_range} listeners of {entity}.
         Data: {json.dumps(data, indent=2)}""", exc_info=True)
        return None


def create_messages(data, entity: str, stats_range: str, from_date: datetime, to_date: datetime, database: str = None) \
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
        database: the name of the database in which the webserver should store the data

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    if database is None:
        database = f"{entity}_listeners_{stats_range}"

    yield {
        "type": "couchdb_data_start",
        "database": database
    }

    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entries in chunked(data, ENTITIES_PER_MESSAGE):
        multiple_entity_stats = []
        for entry in entries:
            processed_stat = parse_one_entity_stats(entry, entity, stats_range)
            multiple_entity_stats.append(processed_stat)

        try:
            model = EntityListenerStatMessage(**{
                "type": "entity_listener",
                "stats_range": stats_range,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "entity": entity,
                "data": multiple_entity_stats,
                "database": database
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error(f"ValidationError while calculating {stats_range} top {entity}:", exc_info=True)

    yield {
        "type": "couchdb_data_end",
        "database": database
    }
