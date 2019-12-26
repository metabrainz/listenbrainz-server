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
PLAYCOUNTS_COUNT = 100

class SparkTestCase(unittest.TestCase):

    ranks = [8]
    lambdas = [0.1]
    iterations = [5]

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
        test_playcounts_df = utils.create_dataframe(test_playcounts, schema=schema)
        utils.save_parquet(test_playcounts_df, TEST_PLAYCOUNTS_PATH)

    @classmethod
    def split_playcounts(cls):
        test_playcounts_df = utils.read_files_from_HDFS(TEST_PLAYCOUNTS_PATH)
        training_data, validation_data, test_data = train_models.preprocess_data(test_playcounts_df)
        return training_data, validation_data, test_data

    @classmethod
    def get_users_df(cls):
        df = utils.create_dataframe([Row(user_name='vansika', user_id=1)], schema=None)
        users_df = df.union(utils.create_dataframe([Row(user_name='rob', user_id=2)], schema=None))
        return users_df

    @classmethod
    def get_recordings_df(cls):
        df = utils.create_dataframe([Row(mb_recording_gid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
            mb_artist_credit_id=1, recording_id=1)], schema=None)
        recordings_df = df.union(utils.create_dataframe([Row(mb_recording_gid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
            mb_artist_credit_id=2, recording_id=2)], schema=None))
        return recordings_df

    @classmethod
    def get_candidate_set(cls):
        df = utils.create_dataframe([Row(user_id=1, recording_id=1)], schema=None)
        candidate_set = df.union(utils.create_dataframe([Row(user_id=2, recording_id=2)], schema=None))
        return candidate_set

    @classmethod
    def get_mapped_listens(cls):
        mapped_listens_row_1 = Row(
            user_name='vansika', artist_msid="a36d6fc9-49d0-4789-a7dd-a2b72369ca45", release_msid="xxxxxx",
            release_name="xxxxxx", artist_name="Less Than Jake", release_mbid="xxxxxx", track_name="Al's War",
            recording_msid="cb6985cd-cc71-4d59-b4fb-2e72796af741", tags=['xxxx'], listened_at=datetime.utcnow(),
            msb_recording_msid="cb6985cd-cc71-4d59-b4fb-2e72796af741", mb_recording_gid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
            msb_artist_msid="a36d6fc9-49d0-4789-a7dd-a2b72369ca45", mb_artist_gids=["181c4177-f33a-441d-b15d-910acaf18b07"],
            mb_artist_credit_id=1
        )
        df = utils.create_dataframe([mapped_listens_row_1], schema=None)

        mapped_listens_row_2 = Row(
            user_name='rob', artist_msid="b36d6fc9-49d0-4789-a7dd-a2b72369ca45", release_msid="xxxxxx",
            release_name="xxxxxx", artist_name="Kishore Kumar", release_mbid="xxxxxx", track_name="Mere Sapno ki Rani",
            recording_msid="bb6985cd-cc71-4d59-b4fb-2e72796af741", tags=['xxxx'], listened_at=datetime.utcnow(),
            msb_recording_msid="bb6985cd-cc71-4d59-b4fb-2e72796af741", mb_recording_gid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
            msb_artist_msid="b36d6fc9-49d0-4789-a7dd-a2b72369ca45", mb_artist_gids=["281c4177-f33a-441d-b15d-910acaf18b07"],
            mb_artist_credit_id=2
        )
        mapped_listens_df = df.union(utils.create_dataframe([mapped_listens_row_2], schema=None))
        return mapped_listens_df
