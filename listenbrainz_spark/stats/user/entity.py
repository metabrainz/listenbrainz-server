import json
import logging
from datetime import datetime
from typing import Iterator, Optional

from pydantic import ValidationError

from data.model.user_entity import UserEntityStatMessage
from data.model.user_artist_stat import UserArtistRecord
from data.model.user_release_stat import UserReleaseRecord
from data.model.user_recording_stat import UserRecordingRecord
from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.stats.user.artist import get_artists
from listenbrainz_spark.stats.user.recording import get_recordings
from listenbrainz_spark.stats.user.release import get_releases
from listenbrainz_spark.utils import get_listens_from_new_dump

logger = logging.getLogger(__name__)

entity_handler_map = {
    "artists": get_artists,
    "releases": get_releases,
    "recordings": get_recordings
}

entity_model_map = {
    "artists": UserArtistRecord,
    "releases": UserReleaseRecord,
    "recordings": UserRecordingRecord
}


def get_entity_stats(entity: str, stats_range: str, message_type="user_entity")\
        -> Iterator[Optional[UserEntityStatMessage]]:
    """ Get the top entity for all users for specified stats_range """
    logger.debug(f"Calculating user_{entity}_{stats_range}...")

    from_date, to_date = get_dates_for_stats_range(stats_range)
    listens_df = get_listens_from_new_dump(from_date, to_date)
    table_name = f"user_{entity}_{stats_range}"
    listens_df.createOrReplaceTempView(table_name)

    handler = entity_handler_map[entity]
    data = handler(table_name)
    messages = create_messages(data=data, entity=entity, stats_range=stats_range,
                               from_date=from_date, to_date=to_date)

    logger.debug("Done!")

    return messages


def create_messages(data, entity: str, stats_range: str, from_date: datetime, to_date: datetime,
                    message_type) \
        -> Iterator[Optional[UserEntityStatMessage]]:
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

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entry in data:
        _dict = entry.asDict(recursive=True)
        total_entity_count = len(_dict[entity])

        # Clip the recordings to top 1000 so that we don't drop messages
        if entity == "recordings" and stats_range == "all_time":
            _dict[entity] = _dict[entity][:1000]

        entity_list = []
        for item in _dict[entity]:
            try:
                entity_list.append(entity_model_map[entity](**item))
            except ValidationError:
                logger.error("Invalid entry in entity stats", exc_info=True)
        try:
            model = UserEntityStatMessage(**{
                "musicbrainz_id": _dict["user_name"],
                "type": message_type,
                "stats_range": stats_range,
                "from_ts": from_ts,
                "to_ts": to_ts,
                "data": entity_list,
                "entity": entity,
                "count": total_entity_count
            })
            result = model.dict(exclude_none=True)
            yield result
        except ValidationError:
            logger.error(f"""ValidationError while calculating {stats_range} top {entity} for user:
             {_dict["user_name"]}. Data: {json.dumps(_dict, indent=3)}""", exc_info=True)
            yield None
