import os
from datetime import datetime

from pyspark import Row
from pyspark.sql.types import StructType, StructField, IntegerType

import listenbrainz_spark
from listenbrainz_spark import utils
from listenbrainz_spark.listens.dump import import_incremental_dump_to_hdfs
from listenbrainz_spark.path import RECOMMENDATION_RECORDING_MAPPED_LISTENS
from listenbrainz_spark.tests import SparkNewTestCase, TEST_DATA_PATH, PLAYCOUNTS_COUNT, TEST_PLAYCOUNTS_PATH
from listenbrainz_spark.hdfs.utils import upload_to_HDFS

class RecommendationsTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(RecommendationsTestCase, cls).setUpClass()
        import_incremental_dump_to_hdfs(cls.dump_loader, 5)
        upload_to_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS, os.path.join(TEST_DATA_PATH, "mapped_listens.parquet"))

    @classmethod
    def get_candidate_set(cls):
        return listenbrainz_spark.session.createDataFrame([
            Row(spark_user_id=1, recording_id=1, user_id=3),
            Row(spark_user_id=2, recording_id=2, user_id=1)
        ])

    @classmethod
    def get_dataframe_metadata(cls, df_id):
        return {
            'dataframe_id': df_id,
            'from_date': datetime(2005, 1, 1),
            'listens_count': 30,
            'playcounts_count': 20,
            'recordings_count': 24,
            'to_date': datetime(2025, 1, 1),
            'users_count': 2,
        }

    @classmethod
    def upload_test_playcounts(cls):
        schema = StructType(
            [
                StructField("spark_user_id", IntegerType()),
                StructField("recording_id", IntegerType()),
                StructField("playcount", IntegerType()),
                StructField("transformed_listencount", IntegerType()),
            ]
        )
        test_playcounts = []
        for i in range(1, PLAYCOUNTS_COUNT // 2 + 1):
            test_playcounts.append([1, 1, 1, 1])
        for i in range(PLAYCOUNTS_COUNT // 2 + 1, PLAYCOUNTS_COUNT + 1):
            test_playcounts.append([2, 2, 1, 1])
        test_playcounts_df = listenbrainz_spark.session.createDataFrame(test_playcounts, schema=schema)
        utils.save_parquet(test_playcounts_df, TEST_PLAYCOUNTS_PATH)

    @classmethod
    def get_model_metadata(cls, model_id):
        return {
            'dataframe_id': 'xxxxx',
            'model_id': model_id,
            'model_html_file': f"{model_id}.html",
            'alpha': 3.0,
            'lmbda': 2.0,
            'iteration': 2,
            'rank': 4,
            'test_data_count': 3,
            'test_rmse': 2.0,
            'training_data_count': 4,
            'validation_data_count': 3,
            'validation_rmse': 2.0,
        }
