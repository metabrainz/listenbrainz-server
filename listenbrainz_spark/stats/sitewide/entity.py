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


incremental_sitewide_map = {
    "artists": AritstSitewideEntity,
    "releases": ReleaseSitewideEntity,
    "recordings": RecordingSitewideEntity,
    "release_groups": ReleaseGroupSitewideEntity,
}


def get_entity_stats(entity: str, stats_range: str) -> Optional[List[SitewideEntityStatMessage]]:
    """ Returns top entity stats for given time period """
    logger.debug(f"Calculating sitewide_{entity}_{stats_range}...")
    entity_cls = incremental_sitewide_map[entity]
    entity_obj: SitewideEntity = entity_cls(stats_range)
    return entity_obj.main()
