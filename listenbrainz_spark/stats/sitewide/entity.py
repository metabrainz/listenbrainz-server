import logging
from datetime import datetime
from typing import List, Optional

from data.model.sitewide_entity import SitewideEntityStatMessage
from data.model.user_artist_stat import ArtistRecord
from data.model.user_recording_stat import RecordingRecord
from data.model.user_release_group_stat import ReleaseGroupRecord
from data.model.user_release_stat import ReleaseRecord
from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME, RELEASE_METADATA_CACHE_DATAFRAME, \
    RELEASE_GROUP_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import get_dates_for_stats_range, SITEWIDE_STATS_ENTITY_LIMIT
from listenbrainz_spark.stats.incremental.sitewide.artist import AritstSitewideEntity
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideEntity
from listenbrainz_spark.stats.incremental.sitewide.recording import RecordingSitewideEntity
from listenbrainz_spark.stats.incremental.sitewide.release import ReleaseSitewideEntity
from listenbrainz_spark.stats.incremental.sitewide.release_group import ReleaseGroupSitewideEntity
from listenbrainz_spark.stats.sitewide.artist import get_artists
from listenbrainz_spark.stats.sitewide.recording import get_recordings
from listenbrainz_spark.stats.sitewide.release import get_releases
from listenbrainz_spark.stats.sitewide.release_group import get_release_groups
from listenbrainz_spark.utils import get_listens_from_dump, read_files_from_HDFS
from pydantic import ValidationError


logger = logging.getLogger(__name__)


entity_handler_map = {
    "artists": get_artists,
    "releases": get_releases,
    "recordings": get_recordings,
    "release_groups": get_release_groups,
}

entity_model_map = {
    "artists": ArtistRecord,
    "releases": ReleaseRecord,
    "recordings": RecordingRecord,
    "release_groups": ReleaseGroupRecord,
}

entity_cache_map = {
    "artists": [ARTIST_COUNTRY_CODE_DATAFRAME],
    "releases": [RELEASE_METADATA_CACHE_DATAFRAME],
    "recordings": [RELEASE_METADATA_CACHE_DATAFRAME],
    "release_groups": [RELEASE_METADATA_CACHE_DATAFRAME, RELEASE_GROUP_METADATA_CACHE_DATAFRAME]
}

incremental_sitewide_map = {
    "artists": AritstSitewideEntity,
    "releases": ReleaseSitewideEntity,
    "recordings": RecordingSitewideEntity,
    "release_groups": ReleaseGroupSitewideEntity,
}


def get_entity_stats(entity: str, stats_range: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Returns top entity stats for given time period """
    logger.debug(f"Calculating sitewide_{entity}_{stats_range}...")
    from_date, to_date = get_dates_for_stats_range(stats_range)
    entity_cls = incremental_sitewide_map[entity]
    entity_obj: SitewideEntity = entity_cls(stats_range)
    data = entity_obj.generate_stats(SITEWIDE_STATS_ENTITY_LIMIT)
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
    count = entry["total_count"]

    entity_list = []
    for item in stats:
        try:
            entity_model_map[entity](**item)
            entity_list.append(item)
        except ValidationError:
            logger.error("Invalid entry in entity stats", exc_info=True)
            count -= 1
    message["count"] = count
    message["data"] = entity_list

    return [message]
