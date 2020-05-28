import uuid
import unittest
from datetime import datetime

import listenbrainz_spark
from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import create_dataframes
from listenbrainz_spark import schema, utils, config, path, hdfs_connection, stats

from pyspark.sql import Row


class CreateDataframeTestCase(SparkTestCase):
    # path used in between test functions of this class
    listens_path = path.LISTENBRAINZ_DATA_DIRECTORY
    mapping_path = path.MBID_MSID_MAPPING
    mapped_listens_path = path.MAPPED_LISTENS

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.date = datetime.utcnow()
        cls.upload_test_listen_to_HDFS()
        cls.upload_test_mapping_to_HDFS()
        cls.upload_test_mapped_listens_to_HDFS()

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    @classmethod
    def upload_test_listen_to_HDFS(cls):
        month, year = cls.date.strftime('%m').lstrip('0'), cls.date.strftime('%Y')

        test_listen = {
            "artist_msid": "a36d6fc9-49d0-4789-a7dd-a2b72369ca45",
            "artist_mbids": [],
            "artist_name": "Less Than Jake",
            "listened_at": cls.date,
            "release_mbid": "", "track_name": "Al's War",
            "recording_msid": "cb6985cd-cc71-4d59-b4fb-2e72796af741",
            "tags": [],
            "user_name": "vansika",
        }

        test_listens_df = utils.create_dataframe(schema.convert_to_spark_json(test_listen), schema.listen_schema)
        utils.save_parquet(test_listens_df, cls.listens_path + '/{}/{}.parquet'.format(year, month))

    @classmethod
    def upload_test_mapping_to_HDFS(cls):
        test_mapping = {
            "msb_recording_msid": "cb6985cd-cc71-4d59-b4fb-2e72796af741",
            "mb_recording_mbid": "3acb406f-c716-45f8-a8bd-96ca3939c2e5",
            "msb_artist_msid": "a36d6fc9-49d0-4789-a7dd-a2b72369ca45",
            "mb_artist_credit_mbids": ["181c4177-f33a-441d-b15d-910acaf18b07"],
            "mb_artist_credit_id": 2157963,
            "mb_release_mbid": "xxxxx",
            "msb_release_msid": "xxxxx",
            "msb_artist_credit_name": "Less Than Jake",
            "msb_artist_credit_name_matchable": "lessthanjake",
            "msb_recording_name": "Al's War",
            "msb_recording_name_matchable": "alswar",
            "msb_release_name": "Easier",
            "msb_release_name_matchable": "easier",
        }

        test_mapping_df = utils.create_dataframe(schema.convert_mapping_to_row(test_mapping), schema.msid_mbid_mapping_schema)
        utils.save_parquet(test_mapping_df, cls.mapping_path)

    @classmethod
    def upload_test_mapped_listens_to_HDFS(cls):
        partial_listen_df = create_dataframes.get_listens_for_training_model_window(cls.date, cls.date, {}, cls.listens_path)
        mapping_df = utils.read_files_from_HDFS(cls.mapping_path)

        mapped_listens = create_dataframes.get_mapped_artist_and_recording_mbids(partial_listen_df, mapping_df)
        utils.save_parquet(mapped_listens, cls.mapped_listens_path)

    def test_get_dates_to_train_data(self):
        train_model_window = 20
        to_date, from_date = create_dataframes.get_dates_to_train_data(train_model_window)
        d = stats.adjust_days(to_date, train_model_window)
        d = stats.replace_days(d, 1)
        self.assertEqual(from_date, d)

    def test_get_listens_for_training_model_window(self):
        metadata = {}
        test_df = create_dataframes.get_listens_for_training_model_window(self.date, self.date, metadata, self.listens_path)
        self.assertEqual(metadata['to_date'], self.date)
        self.assertEqual(metadata['from_date'], self.date)
        self.assertNotIn('artist_mbids', test_df.columns)
        self.assertNotIn('recording_mbid', test_df.columns)

    def test_save_dataframe(self):
        path_ = '/test_df.parquet'
        df = utils.create_dataframe(Row(column1=1, column2=2), schema=None)
        create_dataframes.save_dataframe(df, path_)

        status = utils.path_exists(path_)
        self.assertTrue(status)

    def test_get_mapped_artist_and_recording_mbids(self):
        partial_listen_df = create_dataframes.get_listens_for_training_model_window(self.date, self.date, {}, self.listens_path)
        mapping_df = utils.read_files_from_HDFS(self.mapping_path)

        mapped_listens = create_dataframes.get_mapped_artist_and_recording_mbids(partial_listen_df, mapping_df)
        self.assertEqual(mapped_listens.count(), 1)
        self.assertListEqual(sorted(self.get_mapped_listens().columns), sorted(mapped_listens.columns))
        status = utils.path_exists(path.MAPPED_LISTENS)
        self.assertTrue(status)

    def test_get_users_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, metadata)
        self.assertEqual(users_df.count(), 1)
        self.assertListEqual(sorted(self.get_users_df().columns), sorted(users_df.columns))
        self.assertEqual(metadata['users_count'], users_df.count())

        status = utils.path_exists(path.USERS_DATAFRAME_PATH)
        self.assertTrue(status)

    def test_get_recordings_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, metadata)
        self.assertEqual(recordings_df.count(), 1)
        self.assertListEqual(sorted(self.get_recordings_df().columns), sorted(recordings_df.columns))
        self.assertEqual(metadata['recordings_count'], 1)

        status = utils.path_exists(path.RECORDINGS_DATAFRAME_PATH)
        self.assertTrue(status)

    def test_get_listens_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        listens_df = create_dataframes.get_listens_df(mapped_listens, metadata)
        self.assertEqual(listens_df.count(), 1)
        self.assertListEqual(['mb_recording_mbid', 'user_name'], listens_df.columns)
        self.assertEqual(metadata['listens_count'], 1)

    def test_get_playcounts_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, {})
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, {})
        listens_df = create_dataframes.get_listens_df(mapped_listens, {})

        playcounts_df = create_dataframes.get_playcounts_df(listens_df, recordings_df, users_df, metadata)
        self.assertEqual(playcounts_df.count(), 1)
        self.assertListEqual(['user_id', 'recording_id', 'count'], playcounts_df.columns)
        self.assertEqual(metadata['playcounts_count'], playcounts_df.count())

        status = utils.path_exists(path.PLAYCOUNTS_DATAFRAME_PATH)
        self.assertTrue(status)

    def test_generate_best_model_id(self):
        metadata = {}
        create_dataframes.generate_best_model_id(metadata)
        self.assertTrue(metadata['model_id'])

    def test_save_dataframe_metadata_to_HDFS(self):
        metadata = {
            'from_date': self.date, 'to_date': self.date, 'listens_count': 1, 'model_id': '1', 'playcounts_count': 1,
            'recordings_count': 1, 'updated': True, 'users_count': 1
        }
        create_dataframes.save_dataframe_metadata_to_HDFS(metadata)
        status = utils.path_exists(path.MODEL_METADATA)
        self.assertTrue(status)
