from datetime import datetime, date, time, timedelta
from typing import Iterator, Tuple

from pyspark.sql import DataFrame

from listenbrainz_spark.listens.data import get_listens_from_dump
from listenbrainz_spark.similarity.artist.common import ArtistSimilarityBase


class ListensArtistSimilarity(ArtistSimilarityBase):

    def __init__(self, *, days, session, max_contribution, skip_threshold, threshold, limit, is_production_dataset, only_stage2, top_n_listeners):

        super().__init__(
            name="listens",
            session=session,
            max_contribution=max_contribution,
            skip_threshold=skip_threshold,
            threshold=threshold,
            limit=limit,
            is_production_dataset=is_production_dataset,
            only_stage2=only_stage2,
            top_n_listeners=top_n_listeners
        )
        self.days = days
        self.to_date = datetime.combine(date.today(), time.min)
        self.from_date = self.to_date + timedelta(days=-days)

    def get_algorithm(self) -> str:
        return (
            f"session_based_days_{self.days}_session_{self.session}_"
            f"contribution_{self.max_contribution}_threshold_{self.threshold}_"
            f"limit_{self.limit}_skip_{-self.skip_threshold}_top_n_listeners_{self.top_n_listeners}"
        )

    def get_dataset(self) -> DataFrame:
        return get_listens_from_dump(self.from_date, self.to_date)

    def chunk_dataset(self, dataset: DataFrame) -> Iterator[tuple[str, DataFrame]]:
        yield "all", dataset
