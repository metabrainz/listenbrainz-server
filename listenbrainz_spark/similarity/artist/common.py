import abc
import logging
from string import Template
from typing import Iterator, Tuple

from more_itertools import chunked
from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark import config, hdfs_connection
from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME, ARTIST_CREDIT_MBID_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS

ARTISTS_PER_MESSAGE = 10000
DEFAULT_TRACK_LENGTH = 180  # Default duration in seconds for tracks without duration data
FEATURED_ARTIST_WEIGHT = 0.25  # Weight for featured artists vs main artists

logger = logging.getLogger(__name__)


class ArtistSimilarityBase(abc.ABC):
    """Base class for artist similarity calculations."""

    def __init__(self, name, *, session, max_contribution, skip_threshold, threshold, limit, is_production_dataset, only_stage2, top_n_listeners):
        """Initialize artist similarity calculator.
        
        Args:
            name: The type of listens used
            session: The max time difference between two listens in a listening session (seconds)
            max_contribution: The max contribution a user's listens can make to an artist pair's similarity score
            skip_threshold: The minimum threshold in seconds to mark a listen as skipped
            threshold: The minimum similarity score for two artists to be considered similar
            limit: The maximum number of similar artists to return per artist
            is_production_dataset: Whether this is a production dataset
            only_stage2: Whether to only run the second stage of processing
            top_n_listeners: Number of top listeners per artist to consider for session aggregation
        """
        self.name = name
        self.entity = "artist"
        self.is_production_dataset = is_production_dataset

        self.session = session
        self.max_contribution = max_contribution
        self.skip_threshold = -skip_threshold
        self.threshold = threshold
        self.limit = limit
        self.top_n_listeners = top_n_listeners
        self.only_stage2 = only_stage2

        self.intermediate_dir = f"/similarity/{self.entity}/{self.name}/intermediate-output"
        self.metadata_table = "recording_length"
        self.artist_credit_table = "artist_credit"

    @abc.abstractmethod
    def get_algorithm(self) -> str:
        """Return the algorithm name for this similarity calculator."""
        pass

    @abc.abstractmethod
    def get_dataset(self) -> DataFrame:
        """Get the source DataFrame containing the listens data."""
        pass

    @abc.abstractmethod
    def chunk_dataset(self, dataset: DataFrame) -> Iterator[Tuple[str, DataFrame]]:
        """Split the dataset into chunks for processing.
        
        Yields:
            Tuples of (chunk_name, chunk_dataframe)
        """
        pass

    def setup_tables(self):
        """Set up temporary views needed for similarity calculation."""
        # Load recording lengths
        metadata_df = read_files_from_HDFS(RECORDING_LENGTH_DATAFRAME)
        metadata_df.createOrReplaceTempView(self.metadata_table)
        
        # Load artist credits
        artist_credit_df = read_files_from_HDFS(ARTIST_CREDIT_MBID_DATAFRAME)
        artist_credit_df.createOrReplaceTempView(self.artist_credit_table)

    def get_chunk_index_query(self) -> Template:
        """Construct the SQL query for processing artist similarity chunks."""
        return Template(f"""
            WITH listens AS (
                SELECT l.user_id
                     , BIGINT(l.listened_at) AS listened_at
                     , CAST(COALESCE(r.length / 1000, {DEFAULT_TRACK_LENGTH}) AS BIGINT) AS duration
                     , l.artist_credit_mbids
                     , ac.artist_id
                     , ac.position
                     , ac.join_phrase
                     , any(ac.join_phrase IN ('feat.', 'ｆｅａｔ.', 'ft.', 'συμμ.', 'duet with', 'featuring', 'συμμετέχει', 'ｆｅａｔｕｒｉｎｇ')) 
                       OVER w AS after_ft_jp
                  FROM ${{chunk_table}} l
             LEFT JOIN {self.metadata_table} r
                 USING (recording_mbid)
                  JOIN {self.artist_credit_table} ac
                 USING (artist_credit_id)
                 WHERE l.recording_mbid IS NOT NULL
                   AND l.recording_mbid != ''
                WINDOW w AS (PARTITION BY l.user_id, listened_at, l.recording_mbid ORDER BY ac.position)
            ), grouped_artists AS (
                SELECT user_id
                     , artist_id
                     , count(*) AS listen_count
                  FROM listens
              GROUP BY user_id
                     , artist_id
            ), ranked_artists AS (
                SELECT user_id
                     , artist_id
                     , rank() OVER (PARTITION BY artist_id ORDER BY listen_count DESC) AS rank
                  FROM grouped_artists
            ), top_listeners AS (
                SELECT user_id
                     , artist_id
                  FROM ranked_artists
                 WHERE rank <= {self.top_n_listeners}
            ), ordered AS (
                SELECT user_id
                     , listened_at
                     , listened_at - LAG(listened_at, 1) OVER w - LAG(duration, 1) OVER w AS difference
                     , artist_credit_mbids
                     , artist_id
                     , COALESCE(IF(after_ft_jp, {FEATURED_ARTIST_WEIGHT}, 1), 1) AS similarity
                  FROM listens
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions AS (
                SELECT user_id
                     , COUNT_IF(difference > {self.session}) OVER w AS session_id
                     , LEAD(difference, 1) OVER w < {self.skip_threshold} AS skipped
                     , artist_credit_mbids
                     , artist_id
                     , similarity
                  FROM ordered
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions_filtered AS (
                SELECT s.user_id
                     , s.session_id
                     , s.artist_credit_mbids
                     , s.artist_id
                     , s.similarity
                  FROM sessions s
                 WHERE NOT s.skipped
                   AND EXISTS (
                       SELECT 1
                         FROM top_listeners tl
                        WHERE tl.user_id = s.user_id
                          AND tl.artist_id = s.artist_id
                   )
            ), user_grouped_mbids AS (
                SELECT user_id
                     , s1.artist_id AS id0
                     , s2.artist_id AS id1
                     , s1.similarity * s2.similarity AS similarity
                  FROM sessions_filtered s1
                  JOIN sessions_filtered s2
                 USING (user_id, session_id)
                 WHERE s1.artist_id != s2.artist_id
                   AND s1.artist_credit_mbids != s2.artist_credit_mbids
                   AND s1.artist_id < s2.artist_id
            )
                SELECT id0
                     , id1
                     , LEAST(SUM(similarity), {self.max_contribution}) AS score
                  FROM user_grouped_mbids
              GROUP BY id0
                     , id1
        """)

    def combine_chunks_query(self) -> Template:
        """Construct the SQL query for combining chunks of artist similarity data."""
        return Template(f"""
            WITH thresholded_mbids AS (
                SELECT id0
                     , id1
                     , BIGINT(SUM(score)) AS total_score
                  FROM ${{chunks_table}}
              GROUP BY id0, id1
                HAVING total_score > {self.threshold}
            ), ranked_mbids AS (
                SELECT id0
                     , id1
                     , total_score
                     , rank() OVER w AS rank
                  FROM thresholded_mbids
                WINDOW w AS (PARTITION BY id0 ORDER BY total_score DESC)
            )   SELECT id0 AS mbid0
                     , id1 AS mbid1
                     , total_score AS score
                  FROM ranked_mbids
                  JOIN {self.artist_credit_table} a0
                    ON id0 = a0.artist_id
                  JOIN {self.artist_credit_table} a1
                    ON id1 = a1.artist_id
                 WHERE rank <= {self.limit}
                   AND NOT a0.is_redirect
                   AND NOT a1.is_redirect
              ORDER BY mbid0
                     , score DESC
        """)

    def process_chunked(self):
        dataset = self.get_dataset()
        chunk_query = self.get_chunk_index_query()
        for chunk_name, chunk_df in self.chunk_dataset(dataset):
            logger.info("Processing chunk %s", chunk_name)

            table_name = f"{self.name}_chunk_{chunk_name}"
            chunk_df.createOrReplaceTempView(table_name)
            query = chunk_query.substitute(chunk_table=table_name)
            run_query(query).write.mode("overwrite").parquet(f"{self.intermediate_dir}/{chunk_name}")

    def combine_chunks_output(self) -> DataFrame:
        chunks = hdfs_connection.client.list(self.intermediate_dir)
        chunks_path = [f"{config.HDFS_CLUSTER_URI}{self.intermediate_dir}/{chunk}" for chunk in chunks]
        chunks_table = f"{self.name}_similarity_partial_agg_chunks"
        listenbrainz_spark.session.read.parquet(*chunks_path).createOrReplaceTempView(chunks_table)

        query = self.combine_chunks_query().substitute(chunks_table=chunks_table)
        return run_query(query)

    def create_messages(self, results_df: DataFrame) -> Iterator[dict]:
        """ Generates and yields messages from results DataFrame. """
        message_type = f"{self.name}_similarity_{self.entity}"
        algorithm = self.get_algorithm()

        yield {
            "type": f"{message_type}_start",
            "algorithm": algorithm,
            "is_production_dataset": self.is_production_dataset
        }

        for entries in chunked(results_df.toLocalIterator(), ARTISTS_PER_MESSAGE):
            items = [row.asDict() for row in entries]
            yield {
                "type": message_type,
                "algorithm": algorithm,
                "data": items,
                "is_production_dataset": self.is_production_dataset
            }

        yield {
            "type": f"{message_type}_end",
            "algorithm": algorithm,
            "is_production_dataset": self.is_production_dataset
        }

    def run(self) -> Iterator[dict]:
        self.setup_tables()

        if not self.only_stage2:
            self.process_chunked()
        results_df = self.combine_chunks_output()

        yield from self.create_messages(results_df)
