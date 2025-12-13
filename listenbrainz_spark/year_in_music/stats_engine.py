import logging
from typing import Iterator

from listenbrainz_spark.listens.data import get_listens_from_dump
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.message_creator import MessageCreator
from listenbrainz_spark.stats.incremental.query_provider import QueryProvider

logger = logging.getLogger(__name__)


class YIMStatsEngine:

    def __init__(self, provider: QueryProvider, message_creator: MessageCreator):
        self.provider = provider
        self.message_creator = message_creator
        self.aggregate_table = None

    def run(self) -> Iterator[dict]:
        prefix = self.provider.get_table_prefix()

        table = f"{prefix}_listens"
        listens_df = get_listens_from_dump(
            self.provider.from_date,
            self.provider.to_date,
            include_incremental=False,
            remove_deleted=True
        )
        if listens_df.isEmpty():
            logger.info("No full dump listens found to create partial aggregate from.")
            return
        listens_df.createOrReplaceTempView(table)

        aggregate_query = self.provider.get_aggregate_query(table)
        aggregate_df = run_query(aggregate_query)

        self.aggregate_table = f"{prefix}_aggregate"
        aggregate_df.createOrReplaceTempView(self.aggregate_table)

        results_query = self.provider.get_stats_query(self.aggregate_table)
        results = run_query(results_query)
        for message in self.message_creator.create_messages(results, only_inc=False):
            yield message

        return
