from typing import Iterator, Tuple

from pyspark.sql import DataFrame

from listenbrainz_spark.mlhd.download import MLHD_PLUS_CHUNKS
from listenbrainz_spark.path import MLHD_PLUS_DATA_DIRECTORY
from listenbrainz_spark.similarity.artist.common import ArtistSimilarityBase
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS


class MlhdArtistSimilarity(ArtistSimilarityBase):

    def __init__(self, session, max_contribution, skip_threshold, threshold, limit, is_production_dataset, only_stage2, top_n_listeners):
        super().__init__(
            name="mlhd",
            session=session,
            max_contribution=max_contribution,
            skip_threshold=skip_threshold,
            threshold=threshold,
            limit=limit,
            is_production_dataset=is_production_dataset,
            only_stage2=only_stage2,
            top_n_listeners=top_n_listeners
        )

    def get_algorithm(self) -> str:
        return (
            f"session_based_mlhd_session_{self.session}_"
            f"contribution_{self.max_contribution}_threshold_{self.threshold}_"
            f"limit_{self.limit}_skip_{-self.skip_threshold}_top_n_listeners_{self.top_n_listeners}"
        )

    def get_dataset(self) -> DataFrame:
        return read_files_from_HDFS(MLHD_PLUS_DATA_DIRECTORY)

    def chunk_dataset(self, dataset: DataFrame) -> Iterator[Tuple[str, DataFrame]]:
        for chunk_name in MLHD_PLUS_CHUNKS:
            chunk = dataset.filter(f"user_id LIKE '{chunk_name}%'")
            yield chunk_name, chunk

    def run(self) -> Iterator[dict]:
        if not self.only_stage2:
            run_query("SET spark.sql.shuffle.partitions = 2000").collect()
        
        yield from super().run()
