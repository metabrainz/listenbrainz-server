import abc
import logging
from string import Template
from typing import Iterator

from more_itertools import chunked
from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection, config
from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS

logger = logging.getLogger(__name__)

DEFAULT_TRACK_LENGTH = 180
RECORDINGS_PER_MESSAGE = 10000


class RecordingSimilarityBase(abc.ABC):

    def __init__(self, name, *, session, max_contribution, skip_threshold, threshold, limit, is_production_dataset, only_stage2):
        """ Generate similar recordings based on grouping listening activity into user sessions.

        Args:
            name: the type of listens used
            session: the max time difference between two listens in a listening session
            max_contribution: the max contribution a user's listens can make to a recording pair's similarity score
            threshold: the minimum similarity score for two recordings to be considered similar
            limit: the maximum number of similar recordings to request for a given recording
                (this limit is instructive only, upto 2x number of recordings may be returned)
            skip_threshold: the minimum threshold in seconds to mark a listen as skipped. we cannot just mark a
                negative difference as skip because there may be a difference in track length in MB and music
                services and also issues in timestamping listens.
            is_production_dataset: only determines how the dataset is stored in ListenBrainz database.
            only_stage2: use existing processed intermediate chunks. use this option with caution as the code
                does not check whether the parameters supplied for use in stage 1 are the same as that used to
                generate the existing intermediate chunks.
        """
        self.name = name
        self.entity = "recording"
        self.is_production_dataset = is_production_dataset

        self.session = session
        self.max_contribution = max_contribution
        self.skip_threshold = -skip_threshold
        self.threshold = threshold
        self.limit = limit

        self.only_stage2 = only_stage2
        self.intermediate_dir = f"/similarity/{self.entity}/{self.name}/intermediate-output"
        self.metadata_table = None

    @abc.abstractmethod
    def get_algorithm(self) -> str:
        pass

    def get_chunk_index_query(self) -> Template:
        """
        Constructs a SQL query to compute chunk-based indexing of user sessions and generate
        pairwise scoring of recordings. The query involves multiple steps including filtering
        listens, ordering data by user and time, identifying user sessions, filtering sessions
        based on skip behavior, grouping recording pairs by user, and calculating a final pairwise
        score between recordings based on user sessions and contributions.

        Parameters:
        chunk_table : str
            Name of the chunk table used as the primary source for listen data.

        Returns:
            Template: A template string representing the constructed SQL query,
            with chunk_name as a parameter for substitution.
        """
        return Template(f"""
            WITH listens AS (
                 SELECT user_id
                      , BIGINT(listened_at)
                      , CAST(COALESCE(r.length / 1000, {DEFAULT_TRACK_LENGTH}) AS BIGINT) AS duration
                      , recording_id
                      , artist_credit_mbids
                   FROM ${{chunk_table}} l
                   JOIN {self.metadata_table} r
                  USING (recording_mbid)
                  WHERE l.recording_mbid IS NOT NULL
                    AND l.recording_mbid != ''
            ), ordered AS (
                SELECT user_id
                     , listened_at
                     , listened_at - LAG(listened_at, 1) OVER w - LAG(duration, 1) OVER w AS difference
                     , recording_id
                     , artist_credit_mbids
                  FROM listens
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions AS (
                SELECT user_id
                     -- spark doesn't support window aggregate functions with FILTER clause
                     , COUNT_IF(difference > {self.session}) OVER w AS session_id
                     , LEAD(difference, 1) OVER w < {self.skip_threshold} AS skipped
                     , recording_id
                     , artist_credit_mbids
                  FROM ordered
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions_filtered AS (
                SELECT user_id
                     , session_id
                     , recording_id
                     , artist_credit_mbids
                  FROM sessions
                 WHERE NOT skipped
            ), user_grouped_mbids AS (
                SELECT s1.user_id
                     , s1.recording_id AS id0
                     , s2.recording_id AS id1
                     , COUNT(*) AS part_score
                  FROM sessions_filtered s1
                  JOIN sessions_filtered s2
                    ON s1.user_id = s2.user_id
                   AND s1.session_id = s2.session_id
                   AND s1.recording_id < s2.recording_id
                 WHERE NOT arrays_overlap(s1.artist_credit_mbids, s2.artist_credit_mbids)
              GROUP BY s1.user_id
                     , s1.recording_id
                     , s2.recording_id
            )
                SELECT id0
                     , id1
                     , SUM(LEAST(part_score, {self.max_contribution})) AS score
                  FROM user_grouped_mbids
              GROUP BY id0
                     , id1
        """)

    def combine_chunks_query(self) -> Template:
        """
        Constructs a SQL query template to combine and retrieve data chunks based on a scoring
        threshold, ranking, and other specified criteria.

        Returns:
            Template: A template string representing the constructed SQL query,
            with chunks_table as a parameter for substitution.
        """
        return Template(f"""
            WITH thresholded_mbids AS (
                SELECT id0
                     , id1
                     , SUM(score) AS total_score
                  FROM ${{chunks_table}}
              GROUP BY id0
                     , id1
                HAVING total_score > {self.threshold}
            ), ranked_mbids AS (
                SELECT id0
                     , id1
                     , total_score
                     , rank() OVER w AS rank
                  FROM thresholded_mbids
                WINDOW w AS (PARTITION BY id0 ORDER BY total_score DESC)
            )   SELECT r0.recording_mbid AS mbid0
                     , r1.recording_mbid AS mbid1
                     , total_score AS score
                  FROM ranked_mbids
                  JOIN {self.metadata_table} r0
                    ON id0 = r0.recording_id
                  JOIN {self.metadata_table} r1
                    ON id1 = r1.recording_id
                 WHERE rank <= {self.limit}
                   AND NOT r0.is_redirect
                   AND NOT r1.is_redirect
              ORDER BY mbid0
                     , score DESC
        """)

    @abc.abstractmethod
    def chunk_dataset(self, dataset: DataFrame) -> Iterator[tuple[str, DataFrame]]:
        """ Splits the given dataset into smaller chunks, and returns an iterator of
        the chunk name and the dataframe object. """
        pass

    @abc.abstractmethod
    def get_dataset(self) -> DataFrame:
        """ Returns the DataFrame representing the dataset to be processed. """
        pass

    def create_cache_tables(self):
        """ Creates cache tables for storing metadata information. """
        self.metadata_table = "recording_length"
        read_files_from_HDFS(RECORDING_LENGTH_DATAFRAME).createOrReplaceTempView(self.metadata_table)

    def process_chunked(self):
        """ Processes a dataset in chunks, applying the chunkwise processing query to each
        chunk, and writing the results in Parquet format to an intermediate directory. """
        dataset = self.get_dataset()
        chunk_query = self.get_chunk_index_query()
        for chunk_name, chunk_df in self.chunk_dataset(dataset):
            logger.info("Processing chunk %s", chunk_name)

            table_name = f"{self.name}_chunk_{chunk_name}"
            chunk_df.createOrReplaceTempView(table_name)
            query = chunk_query.substitute(chunk_table=table_name)
            run_query(query).write.mode("overwrite").parquet(f"{self.intermediate_dir}/{chunk_name}")

    def combine_chunks_output(self) -> DataFrame:
        """ Loads all the data chunks into a single DataFrame and combines them by performing aggregating
        the scores across users and trims the dataset by filtering out low score recordings and only keeping
        the limit number of recording pairs. """
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

        for entries in chunked(results_df.toLocalIterator(), RECORDINGS_PER_MESSAGE):
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
        """ Executes the data processing pipeline and yields processed messages.

        This method orchestrates the data pipeline by first creating necessary cache
        tables, then processing data in chunks if stage 2 processing is not the only
        desired operation. After chunked processing, it combines the output of all
        chunks into a single data frame and generates messages from the resulting data.
        """
        self.create_cache_tables()

        if not self.only_stage2:
            self.process_chunked()
        results_df = self.combine_chunks_output()

        yield from self.create_messages(results_df)
