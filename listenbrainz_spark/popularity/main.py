import logging
from datetime import datetime

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.popularity.common import PopularityMessageCreator
from listenbrainz_spark.popularity.listens import PopularityProvider, TopPerArtistPopularityProvider
from listenbrainz_spark.popularity.mlhd import MlhdStatsEngine
from listenbrainz_spark.stats.incremental.incremental_stats_engine import IncrementalStatsEngine
from listenbrainz_spark.stats.incremental.range_selector import FromToRangeListenRangeSelector
from listenbrainz_spark.listens.data import get_latest_listen_ts

logger = logging.getLogger(__name__)


def main(type, entity, mlhd):
    """ Generate popularity data for MLHD data. """
    start = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    end = get_latest_listen_ts()

    selector = FromToRangeListenRangeSelector(start, end)
    selector.stats_range = type

    if type == "popularity":
        provider = PopularityProvider(selector, entity)
    else:
        provider = TopPerArtistPopularityProvider(selector, entity)
    message_creator = PopularityMessageCreator(entity=entity, message_type=type, is_mlhd=mlhd)

    if mlhd:
        engine = MlhdStatsEngine(provider, message_creator)
    else:
        engine = IncrementalStatsEngine(provider, message_creator)
    return engine.run()
