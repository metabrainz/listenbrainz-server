from typing import Iterator

from pyspark.sql import DataFrame

from listenbrainz_spark.mlhd.download import MLHD_PLUS_CHUNKS
from listenbrainz_spark.path import MLHD_PLUS_DATA_DIRECTORY
from listenbrainz_spark.similarity.recording.common import RecordingSimilarityBase
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS


class MlhdRecordingSimilarity(RecordingSimilarityBase):

    def __init__(self, session, max_contribution, skip_threshold, threshold, limit, is_production_dataset, only_stage2):
        super().__init__(
            "mlhd",
            session=session,
            max_contribution=max_contribution,
            skip_threshold=skip_threshold,
            threshold=threshold,
            limit=limit,
            is_production_dataset=is_production_dataset,
            only_stage2=only_stage2,
        )

    def get_algorithm(self) -> str:
        return f"session_based_mlhd_session_{self.session}_contribution_{self.max_contribution}_threshold_{self.threshold}_limit_{self.limit}_skip_{-self.skip_threshold}"

    def get_dataset(self) -> DataFrame:
        return read_files_from_HDFS(MLHD_PLUS_DATA_DIRECTORY)

    def chunk_dataset(self, dataset: DataFrame) -> Iterator[tuple[str, DataFrame]]:
        for chunk_name in MLHD_PLUS_CHUNKS:
            chunk = dataset.filter(f"user_id LIKE '{chunk_name}%'")
            yield chunk_name, chunk

    def run(self) -> Iterator[dict]:
        if not self.only_stage2:
            run_query("SET spark.sql.shuffle.partitions = 2000").collect()

        yield from super().run()
