import json
import logging
from datetime import datetime
from typing import List, Optional

from data.model.sitewide_artist_stat import SitewideArtistRecord
from data.model.sitewide_entity import SitewideEntityStatMessage
from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.stats.sitewide.artist import get_artists
from listenbrainz_spark.utils import get_listens_from_new_dump
from pydantic import ValidationError


logger = logging.getLogger(__name__)


entity_handler_map = {
    "artists": get_artists,
}

entity_model_map = {
    "artists": SitewideArtistRecord
}


def get_entity_stats(entity: str, stats_range: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Returns top entity stats for given time period """
    logger.debug(f"Calculating sitewide_{entity}_{stats_range}...")

    from_date, to_date = get_dates_for_stats_range(stats_range)
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
