import os

from pyspark import Row

import listenbrainz_spark
from listenbrainz_spark import utils
from listenbrainz_spark.path import LISTENBRAINZ_NEW_DATA_DIRECTORY, RECOMMENDATION_RECORDING_MAPPED_LISTENS
from listenbrainz_spark.tests import SparkNewTestCase, TEST_DATA_PATH


class RecommendationsTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(RecommendationsTestCase, cls).setUpClass()
        utils.upload_to_HDFS(LISTENBRAINZ_NEW_DATA_DIRECTORY, os.path.join(TEST_DATA_PATH, 'rec_listens.parquet'))
        utils.upload_to_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS, os.path.join(TEST_DATA_PATH, 'mapped_listens.parquet'))

    @classmethod
    def tearDownClass(cls) -> None:
        super(RecommendationsTestCase, cls).tearDownClass()
        cls.delete_dir()

    @classmethod
    def get_candidate_set(cls):
        return listenbrainz_spark.session.createDataFrame([
            Row(user_id=1, recording_id=1, user_name='vansika'),
            Row(user_id=2, recording_id=2, user_name='rob')
        ])

    @classmethod
    def get_dataframe_metadata(cls, df_id):
        return {
            'dataframe_id': df_id,
            'from_date': cls.begin_date,
            'listens_count': 30,
            'playcounts_count': 20,
            'recordings_count': 24,
            'to_date': cls.end_date,
            'users_count': 2,
        }
