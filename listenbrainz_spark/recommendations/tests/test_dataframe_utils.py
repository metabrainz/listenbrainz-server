import re
from datetime import datetime

from listenbrainz_spark.tests import SparkTestCase

from listenbrainz_spark.recommendations import dataframe_utils
from listenbrainz_spark import utils, path, stats
from listenbrainz_spark.stats.utils import get_latest_listen_ts
import listenbrainz_spark.utils.mapping as mapping_utils

from pyspark.sql import Row


class DataframeUtilsTestCase(SparkTestCase):
    listens_path = path.LISTENBRAINZ_DATA_DIRECTORY
    mapping_path = path.MBID_MSID_MAPPING

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upload_test_listen_to_hdfs(cls.listens_path)
        cls.upload_test_mapping_to_hdfs(cls.mapping_path)

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    def test_generate_dataframe_id(self):
        prefix = 'listenbrainz-recommendation-dataframe'
        dataframe_id = dataframe_utils.get_dataframe_id(prefix)
        assert re.match('{}-*'.format(prefix), dataframe_id)

    def test_get_dates_to_train_data(self):
        train_model_window = 12
        to_date, from_date = dataframe_utils.get_dates_to_train_data(train_model_window)
        d = stats.offset_days(to_date, train_model_window)
        d = stats.replace_days(d, 1)
        # refer to testdata/listens.json
        self.assertEqual(to_date, datetime(2019, 1, 21, 0, 0))
        self.assertEqual(from_date, d)

    def test_get_listens_for_training_model_window(self):
        to_date = get_latest_listen_ts()
        from_date = stats.offset_days(to_date, 2)
        print(to_date, from_date)
        test_df = dataframe_utils.get_listens_for_training_model_window(to_date, from_date, self.listens_path)
        self.assertIn('artist_name_matchable', test_df.columns)
        self.assertIn('track_name_matchable', test_df.columns)
        self.assertEqual(test_df.count(), 11)

    def test_get_mapped_artist_and_recording_mbids(self):
        to_date = get_latest_listen_ts()
        partial_listen_df = dataframe_utils.get_listens_for_training_model_window(to_date, to_date, self.listens_path)

        df = utils.read_files_from_HDFS(self.mapping_path)
        mapping_df = mapping_utils.get_unique_rows_from_mapping(df)
        mapped_listens_path = '/mapped_listens.parquet'

        mapped_listens = dataframe_utils.get_mapped_artist_and_recording_mbids(partial_listen_df, mapping_df)
        self.assertEqual(mapped_listens.count(), 8)

        cols = [
            'listened_at',
            'mb_artist_credit_id',
            'mb_artist_credit_mbids',
            'mb_recording_mbid',
            'mb_release_mbid',
            'msb_artist_credit_name_matchable',
            'msb_recording_name_matchable',
            'user_name'
        ]

        self.assertListEqual(sorted(cols), sorted(mapped_listens.columns))

    def test_save_dataframe(self):
        path_ = '/test_df.parquet'
        df = utils.create_dataframe(Row(column1=1, column2=2), schema=None)
        dataframe_utils.save_dataframe(df, path_)

        status = utils.path_exists(path_)
        self.assertTrue(status)
