import os
import uuid
import unittest
from datetime import datetime

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection, utils, config
from listenbrainz_spark.recommendations import train_models

from pyspark.sql import Row
import pyspark.sql.functions as f
from pyspark.sql.types import StructType, StructField, IntegerType

TEST_PLAYCOUNTS_PATH = '/tests/playcounts.parquet'
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'testdata')
PLAYCOUNTS_COUNT = 100


class SparkTestCase(unittest.TestCase):

    ranks = [8]
    lambdas = [0.1]
    iterations = [5]
    alpha = 3.0

    @classmethod
    def setUpClass(cls):
        listenbrainz_spark.init_test_session('spark-test-run-{}'.format(str(uuid.uuid4())))
        hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
        cls.app = utils.create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()
        listenbrainz_spark.context.stop()

    @classmethod
    def delete_dir(cls):
        walk = utils.hdfs_walk('/', depth=1)
        # dirs in '/'
        dirs = next(walk)[1]
        for directory in dirs:
            utils.delete_dir(os.path.join('/', directory), recursive=True)

    @classmethod
    def upload_test_playcounts(cls):
        schema = StructType(
            [
                StructField("user_id", IntegerType()),
                StructField("recording_id", IntegerType()),
                StructField("count", IntegerType())
            ]
        )
        test_playcounts = []
        for i in range(1, PLAYCOUNTS_COUNT // 2 + 1):
            test_playcounts.append([1, 1, 1])
        for i in range(PLAYCOUNTS_COUNT // 2 + 1, PLAYCOUNTS_COUNT + 1):
            test_playcounts.append([2, 2, 1])
        test_playcounts_df = listenbrainz_spark.session.createDataFrame(test_playcounts, schema=schema)
        utils.save_parquet(test_playcounts_df, TEST_PLAYCOUNTS_PATH)

    @classmethod
    def split_playcounts(cls):
        test_playcounts_df = utils.read_files_from_HDFS(TEST_PLAYCOUNTS_PATH)
        training_data, validation_data, test_data = train_models.preprocess_data(test_playcounts_df)
        return training_data, validation_data, test_data

    @classmethod
    def get_users_df(cls):
        df = utils.create_dataframe(
            Row(
                user_name='vansika',
                user_id=1
            ),
            schema=None
        )
        users_df = df.union(utils.create_dataframe(
            Row(
                user_name='rob',
                user_id=2
            ),
            schema=None
        ))
        return users_df

    @classmethod
    def get_recordings_df(cls):
        df = utils.create_dataframe(
            Row(
                mb_artist_credit_id=1,
                mb_artist_credit_mbids=["181c4177-f33a-441d-b15d-910acaf18b07"],
                mb_recording_mbid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
                mb_release_mbid="xxxxxx",
                msb_artist_credit_name_matchable="lessthanjake",
                recording_id=1,
                track_name="Al's War",
            ),
            schema=None
        )
        recordings_df = df.union(utils.create_dataframe(
            Row(
                mb_artist_credit_id=2,
                mb_artist_mbids=["281c4177-f33a-441d-b15d-910acaf18b07"],
                mb_recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                mb_release_mbid="xxxxxx",
                msb_artist_credit_name_matchable="kishorekumar",
                recording_id=2,
                track_name="Mere Sapno ki Rani",
            ),
            schema=None
        ))
        return recordings_df

    @classmethod
    def get_candidate_set(cls):
        df = utils.create_dataframe(
            Row(
                user_id=1,
                recording_id=1,
                user_name='vansika'
            ),
            schema=None
        )
        candidate_set = df.union(utils.create_dataframe(
            Row(
                user_id=2,
                recording_id=2,
                user_name='rob'
            ),
            schema=None
        ))
        return candidate_set

    @classmethod
    def get_mapped_listens(cls):
        mapped_listens_row_1 = Row(
            listened_at=datetime.utcnow(),
            mb_artist_credit_id=1,
            mb_artist_credit_mbids=["181c4177-f33a-441d-b15d-910acaf18b07"],
            mb_recording_mbid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
            mb_release_mbid="xxxxxx",
            msb_artist_credit_name_matchable="lessthanjake",
            track_name="Al's War",
            user_name='vansika',
        )
        df = utils.create_dataframe(mapped_listens_row_1, schema=None)

        mapped_listens_row_2 = Row(
            listened_at=datetime.utcnow(),
            mb_artist_credit_id=2,
            mb_artist_mbids=["281c4177-f33a-441d-b15d-910acaf18b07"],
            mb_recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
            mb_release_mbid="xxxxxx",
            msb_artist_credit_name_matchable="kishorekumar",
            track_name="Mere Sapno ki Rani",
            user_name='rob',
        )
        mapped_listens_df = df.union(utils.create_dataframe(mapped_listens_row_2, schema=None))
        return mapped_listens_df

    def path_to_data_file(self, file_name):
        """ Returns the path of the test data file relative to listenbrainz_spark/test/__init__.py.

            Args:
                file_name: the name of the data file
        """
        return os.path.join(TEST_DATA_PATH, file_name)
