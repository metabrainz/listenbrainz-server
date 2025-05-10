from datetime import datetime, date, time, timedelta
from typing import Iterator

from pyspark.sql import DataFrame

from listenbrainz_spark.listens.data import get_listens_from_dump
from listenbrainz_spark.similarity.recording.common import RecordingSimilarityBase


class ListensRecordingSimilarity(RecordingSimilarityBase):

    def __init__(self, *, days, session, max_contribution, skip_threshold, threshold, limit, is_production_dataset, only_stage2):
        super().__init__(
            "listens",
            session=session,
            max_contribution=max_contribution,
            skip_threshold=skip_threshold,
            threshold=threshold,
            limit=limit,
            is_production_dataset=is_production_dataset,
            only_stage2=only_stage2,
        )
        self.days = days
        self.to_date = datetime.combine(date.today(), time.min)
        self.from_date = self.to_date + timedelta(days=-days)

    def get_algorithm(self) -> str:
        return f"session_based_days_{self.days}_session_{self.session}_contribution_{self.max_contribution}_threshold_{self.threshold}_limit_{self.limit}_skip_{-self.skip_threshold}"

    def get_dataset(self) -> DataFrame:
        return get_listens_from_dump(self.from_date, self.to_date)

    def chunk_dataset(self, dataset: DataFrame) -> Iterator[tuple[str, DataFrame]]:
        yield "all", dataset
