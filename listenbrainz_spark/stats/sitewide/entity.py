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
    "artists": get_artists,
}

entity_model_map = {
    "artists": SitewideArtistRecord
}


def get_entity_week(entity: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the weekly sitewide top entity """
    to_date = get_last_monday(get_latest_listen_ts())
    from_date = offset_days(to_date, 7)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    return _get_entity_stats(entity, "week", from_date, to_date)


def get_entity_month(entity: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the montly sitewide top entity """
    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    return _get_entity_stats(entity, "month", from_date, to_date)


def get_entity_year(entity: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the yearly sitewide top entity """
    to_date = get_latest_listen_ts()
    from_date = replace_days(replace_months(to_date, 1), 1)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    return _get_entity_stats(entity, "year", from_date, to_date)


def get_entity_all_time(entity: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Get the all_time sitewide top entity """
    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    # Set time to 00:00
    from_date = datetime(from_date.year, from_date.month, from_date.day)
    return _get_entity_stats(entity, "all_time", from_date, to_date)


def _get_entity_stats(entity: str, stats_range: str, from_date: datetime, to_date: datetime) \
        -> Optional[List[SitewideEntityStatMessage]]:
    """ Returns top entity stats for given time period """
    logger.debug(f"Calculating sitewide_{entity}_{stats_range}...")

    listens_df = get_listens_from_new_dump(from_date, to_date)
    table_name = f"sitewide_{entity}_{stats_range}"
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)

    messages = create_messages(data=data, entity=entity, stats_range=stats_range,
                               from_date=from_date, to_date=to_date)

    logger.debug("Done!")

    return messages


def create_messages(data, entity: str, stats_range: str, from_date: datetime, to_date: datetime):
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data: Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_date: The start time of the stats
        to_date: The end time of the stats

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    message = {
        "type": "sitewide_entity",
        "stats_range": stats_range,
        "from_ts": int(from_date.timestamp()),
        "to_ts": int(to_date.timestamp()),
        "entity": entity,
    }
    entry = next(data).asDict(recursive=True)
    stats = entry["stats"]
    message["count"] = len(stats)

    entity_list = []
    for item in stats:
        try:
            entity_list.append(entity_model_map[entity](**item))
        except ValidationError:
            logger.error("Invalid entry in entity stats", exc_info=True)
    message["data"] = entity_list

    try:
        model = SitewideEntityStatMessage(**message)
        result = model.dict(exclude_none=True)
        return [result]
    except ValidationError:
        logger.error(f"""ValidationError while calculating {stats_range} sitewide top {entity}. 
        Data: {json.dumps(message, indent=4)}""", exc_info=True)
        return None
