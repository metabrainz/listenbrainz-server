import json
import logging
from datetime import datetime
from typing import List, Optional

from data.model.sitewide_artist_stat import SitewideArtistRecord
from data.model.sitewide_entity import SitewideEntityStatMessage
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats import offset_days, replace_days, get_last_monday, replace_months
from listenbrainz_spark.stats.sitewide.artist import get_artists
from listenbrainz_spark.utils import get_listens_from_new_dump, get_latest_listen_ts
from pydantic import ValidationError


logger = logging.getLogger(__name__)


entity_handler_map = {
    'artists': get_artists,
}

entity_model_map = {
    'artists': SitewideArtistRecord
}


def get_entity_week(entity: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the weekly sitewide top entity """
    logger.debug(f"Calculating sitewide_{entity}_week...")

    to_date = get_last_monday(get_latest_listen_ts())
    from_date = offset_days(to_date, 7)

    listens_df = get_listens_from_new_dump(from_date, to_date)
    table_name = f'sitewide_{entity}_week'
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range='week',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_entity_month(entity: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the montly sitewide top entity """
    logger.debug(f"Calculating sitewide_{entity}_month...")

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)

    listens_df = get_listens_from_new_dump(from_date, to_date)
    table_name = f'sitewide_{entity}_month'
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)

    messages = create_messages(data=data, entity=entity, stats_range='month',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_entity_year(entity: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the yearly sitewide top entity """
    logger.debug(f"Calculating sitewide_{entity}_year...")

    to_date = get_latest_listen_ts()
    from_date = replace_days(replace_months(to_date, 1), 1)

    listens_df = get_listens_from_new_dump(from_date, to_date)
    table_name = f'sitewide_{entity}_year'
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)

    messages = create_messages(data=data, entity=entity, stats_range='year',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def get_entity_all_time(entity: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the all_time sitewide top entity """
    logger.debug(f"Calculating sitewide_{entity}_all_time...")

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    listens_df = get_listens_from_new_dump(from_date, to_date)
    table_name = f'sitewide_{entity}_all_time'
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)

    messages = create_messages(data=data, entity=entity, stats_range='all_time',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    logger.debug("Done!")

    return messages


def create_messages(data, entity: str, stats_range: str, from_ts: float, to_ts: float):
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data (iterator): Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_ts: The UNIX timestamp of start time of the stats
        to_ts: The UNIX timestamp of end time of the stats

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    message = {
        'type': 'sitewide_entity',
        'stats_range': stats_range,
        'from_ts': from_ts,
        'to_ts': to_ts,
        'entity': entity,
    }
    entry = next(data).asDict(recursive=True)
    stats = entry['stats']
    message['count'] = len(stats)

    entity_list = []
    for item in stats:
        try:
            entity_list.append(entity_model_map[entity](**item))
        except ValidationError:
            logger.error("Invalid entry in entity stats", exc_info=True)
    message['data'] = entity_list

    try:
        model = SitewideEntityStatMessage(**message)
        result = model.dict(exclude_none=True)
        return [result]
    except ValidationError:
        logger.error(f"""ValidationError while calculating {stats_range} sitewide top {entity}. 
        Data: {json.dumps(message, indent=4)}""", exc_info=True)
        return None
