import abc
from datetime import datetime
from pathlib import Path
from typing import List

from pyspark.errors import AnalysisException
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.config import HDFS_CLUSTER_URI
from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.schema import BOOKKEEPING_SCHEMA
from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.utils import read_files_from_HDFS, logger, get_listens_from_dump


class IncrementalStats(abc.ABC):
    """
    Provides a framework for generating incremental statistics for a given entity (e.g., users, tracks)
    over a specified date range.

    In the ListenBrainz Spark cluster, full dump listens (which remain constant for ~15 days) and incremental listens
    (ingested daily) are the two main sources of data. Incremental listens are cleared whenever a new full dump is
    imported. Aggregating full dump listens daily for various statistics is inefficient since this data does not
    change.

    To optimize this process:

    1. A partial aggregate is generated from the full dump listens the first time a stat is requested. This partial
       aggregate is stored in HDFS for future use, eliminating the need for redundant full dump aggregation.
    2. Incremental listens are aggregated daily. Although all incremental listens since the full dump’s import are
       used (not just today’s), this introduces some redundant computation.
    3. The incremental aggregate is combined with the existing partial aggregate, forming a combined aggregate from
       which final statistics are generated.

    For non-sitewide statistics, further optimization is possible:

        If an entity’s listens (e.g., for a user) are not present in the incremental listens, its statistics do not
        need to be recalculated. Similarly, entity-level listener stats can skip recomputation when relevant data
        is absent in incremental listens.
    """
