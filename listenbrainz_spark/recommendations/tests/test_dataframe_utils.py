import re
from datetime import datetime

from listenbrainz_spark.tests import SparkNewTestCase
from listenbrainz_spark.hdfs.utils import path_exists
from listenbrainz_spark.recommendations import dataframe_utils
from listenbrainz_spark import utils

from pyspark.sql import Row


class DataframeUtilsTestCase(SparkNewTestCase):

    @classmethod
    def setUpClass(cls):
        super(DataframeUtilsTestCase, cls).setUpClass()
        cls.upload_test_listens()

    @classmethod
    def tearDownClass(cls):
        cls.delete_uploaded_listens()
        super(DataframeUtilsTestCase, cls).tearDownClass()

    def test_generate_dataframe_id(self):
        prefix = 'listenbrainz-recommendation-dataframe'
        dataframe_id = dataframe_utils.get_dataframe_id(prefix)
        assert re.match('{}-*'.format(prefix), dataframe_id)

    def test_get_dates_to_train_data(self):
        train_model_window = 12
        to_date, from_date = dataframe_utils.get_dates_to_train_data(train_model_window)
        self.assertEqual(to_date, datetime(2021, 8, 9, 12, 22, 43))
        self.assertEqual(from_date, datetime(2021, 7, 1, 12, 22, 43))

    def test_save_dataframe(self):
        path_ = '/test_df.parquet'
        df = utils.create_dataframe(Row(column1=1, column2=2), schema=None)
        dataframe_utils.save_dataframe(df, path_)

        status = path_exists(path_)
        self.assertTrue(status)
