import json
import logging
from datetime import datetime
from typing import Iterator, Optional, Dict, List

from more_itertools import chunked
from pydantic import ValidationError

from data.model.entity_listener_stat import EntityListenerRecord, ArtistListenerRecord, \
    ReleaseGroupListenerRecord
from listenbrainz_spark.path import RELEASE_METADATA_CACHE_DATAFRAME, ARTIST_COUNTRY_CODE_DATAFRAME, \
    RELEASE_GROUP_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.stats.incremental.listener.artist import ArtistEntityListener
from listenbrainz_spark.stats.incremental.listener.release_group import ReleaseGroupEntityListener
from listenbrainz_spark.stats.listener import artist, release_group

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

incremental_entity_obj_map = {
    "artists": ArtistEntityListener(),
    "release_groups": ReleaseGroupEntityListener(),
}

ENTITIES_PER_MESSAGE = 10000  # number of entities per message
NUMBER_OF_TOP_LISTENERS = 10  # number of top listeners to retain for user stats


def get_listener_stats(entity: str, stats_range: str, database: str = None) -> Iterator[Optional[Dict]]:
    """ Get the top listeners for all entity for specified stats_range """
    logger.debug(f"Calculating {entity}_listeners_{stats_range}...")

    from_date, to_date = get_dates_for_stats_range(stats_range)
    entity_obj = incremental_entity_obj_map[entity]
    only_inc_entities, data = entity_obj.generate_stats(stats_range, from_date, to_date, NUMBER_OF_TOP_LISTENERS)
    return create_messages(only_inc_entities, data=data, entity=entity, stats_range=stats_range, from_date=from_date,
                           to_date=to_date, database=database)


def parse_one_entity_stats(entry, entity: str, stats_range: str) \
        -> Optional[EntityListenerRecord]:
    try:
        data = entry.asDict(recursive=True)
        entity_model_map[entity](**data)
        return data
    except ValidationError:
        logger.error(f"""ValidationError while calculating {stats_range} listeners of {entity}.
         Data: {json.dumps(data, indent=2)}""", exc_info=True)
        return None


def create_messages(only_inc_entities, data, entity: str, stats_range: str, from_date: datetime, to_date: datetime, database: str = None) \
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
        database = f"{entity}_listeners_{stats_range}_{datetime.today().strftime('%Y%m%d')}"

    if only_inc_entities:
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

        yield {
            "type": "entity_listener",
            "stats_range": stats_range,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "entity": entity,
            "data": multiple_entity_stats,
            "database": database
        }

    if only_inc_entities:
        yield {
            "type": "couchdb_data_end",
            "database": database
        }
