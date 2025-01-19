import logging
from datetime import datetime

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.popularity.common import PopularityMessageCreator
from listenbrainz_spark.popularity.listens import PopularityProvider, TopPerArtistPopularityProvider
from listenbrainz_spark.popularity.mlhd import MlhdAggregator
from listenbrainz_spark.stats.incremental.aggregator import Aggregator
from listenbrainz_spark.stats.incremental.range_selector import FromToRangeListenRangeSelector
from listenbrainz_spark.utils import get_latest_listen_ts

logger = logging.getLogger(__name__)


def main(type, entity, is_mlhd):
    """ Generate popularity data for MLHD data. """
    start = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    end = get_latest_listen_ts()

    selector = FromToRangeListenRangeSelector(start, end)
    selector.stats_range = type

    if type == "popularity":
        provider = PopularityProvider(selector, entity)
    else:
        provider = TopPerArtistPopularityProvider(selector, entity)
    message_creator = PopularityMessageCreator(entity=entity, message_type=type, is_mlhd=is_mlhd)

    if is_mlhd:
        aggregator = MlhdAggregator(provider, message_creator)
    else:
        aggregator = Aggregator(provider, message_creator)
    return aggregator.main()
