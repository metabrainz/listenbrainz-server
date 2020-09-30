import re
import uuid
import unittest
from datetime import datetime

import listenbrainz_spark
from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import create_dataframes
from listenbrainz_spark.stats.utils import get_latest_listen_ts
from listenbrainz_spark import schema, utils, config, path, hdfs_connection, stats

from pyspark.sql import Row
import time


class CreateDataframeTestCase(SparkTestCase):
    # path used in between test functions of this class
    listens_path = path.LISTENBRAINZ_DATA_DIRECTORY
    mapping_path = path.MBID_MSID_MAPPING
    mapped_listens_path = path.MAPPED_LISTENS

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upload_test_listen_to_hdfs(cls.listens_path)
        cls.upload_test_mapping_to_hdfs(cls.mapping_path)
        cls.upload_test_mapped_listens_to_hdfs(cls.listens_path, cls.mapping_path, cls.mapped_listens_path)

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    def test_get_dates_to_train_data(self):
        train_model_window = 20
        to_date, from_date = create_dataframes.get_dates_to_train_data(train_model_window)
        d = stats.offset_days(to_date, train_model_window)
        d = stats.replace_days(d, 1)
        self.assertEqual(from_date, d)

    def test_get_listens_for_training_model_window(self):
        metadata = {}
        to_date = get_latest_listen_ts()
        from_date = stats.offset_days(to_date, 2)
        test_df = create_dataframes.get_listens_for_training_model_window(to_date, from_date, metadata, self.listens_path)
        self.assertEqual(metadata['to_date'], to_date)
        self.assertEqual(metadata['from_date'], from_date)
        self.assertIn('artist_name_matchable', test_df.columns)
        self.assertIn('track_name_matchable', test_df.columns)
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

        df = utils.read_files_from_HDFS(self.mapping_path)
        mapping_df = utils.get_unique_rows_from_mapping(df)

        mapped_listens = create_dataframes.get_mapped_artist_and_recording_mbids(partial_listen_df, mapping_df)
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
        status = utils.path_exists(path.MAPPED_LISTENS)
        self.assertTrue(status)

    def test_get_users_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, metadata)
        self.assertEqual(users_df.count(), 2)
        self.assertListEqual(sorted(self.get_users_df().columns), sorted(users_df.columns))
        self.assertEqual(metadata['users_count'], users_df.count())

        status = utils.path_exists(path.USERS_DATAFRAME_PATH)
        self.assertTrue(status)

    def test_get_recordings_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, metadata)
        self.assertEqual(recordings_df.count(), 3)
        self.assertListEqual(sorted(self.get_recordings_df().columns), sorted(recordings_df.columns))
        self.assertEqual(metadata['recordings_count'], 3)

        status = utils.path_exists(path.RECORDINGS_DATAFRAME_PATH)
        self.assertTrue(status)

    def test_get_listens_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        listens_df = create_dataframes.get_listens_df(mapped_listens, metadata)
        self.assertEqual(listens_df.count(), 8)
        self.assertListEqual(['mb_recording_mbid', 'user_name'], listens_df.columns)
        self.assertEqual(metadata['listens_count'], 8)

    def test_save_playcounts_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, {})
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, {})
        listens_df = create_dataframes.get_listens_df(mapped_listens, {})

        create_dataframes.save_playcounts_df(listens_df, recordings_df, users_df, metadata)
        playcounts_df = utils.read_files_from_HDFS(path.PLAYCOUNTS_DATAFRAME_PATH)
        self.assertEqual(playcounts_df.count(), 5)

        self.assertListEqual(['user_id', 'recording_id', 'count'], playcounts_df.columns)
        self.assertEqual(metadata['playcounts_count'], playcounts_df.count())

    def test_generate_dataframe_id(self):
        metadata = {}
        create_dataframes.generate_dataframe_id(metadata)
        assert re.match('{}-*'.format(config.DATAFRAME_ID_PREFIX), metadata['dataframe_id'])

    def test_save_dataframe_metadata_to_HDFS(self):
        df_id = "3acb406f-c716-45f8-a8bd-96ca3939c2e5"
        metadata = self.get_dataframe_metadata(df_id)
        create_dataframes.save_dataframe_metadata_to_hdfs(metadata)

        status = utils.path_exists(path.DATAFRAME_METADATA)
        self.assertTrue(status)

        df = utils.read_files_from_HDFS(path.DATAFRAME_METADATA)
        self.assertTrue(sorted(df.columns), sorted(schema.dataframe_metadata_schema.fieldNames()))

    def test_get_data_missing_from_musicbrainz(self):
        partial_listen_df = create_dataframes.get_listens_for_training_model_window(self.date, self.date, {}, self.listens_path)
        mapping_df = utils.read_files_from_HDFS(self.mapping_path)

        itr = create_dataframes.get_data_missing_from_musicbrainz(partial_listen_df, mapping_df)

        received_data = []
        for row in itr:
            received_data.append(
                {
                    'user_name': 'vansika',
                    'artist_msid': row.artist_msid,
                    'artist_name': row.artist_name,
                    'listened_at': str(row.listened_at),
                    'recording_msid': row.recording_msid,
                    'release_msid': row.release_msid,
                    'release_name': row.release_name,
                    'track_name': row.track_name,
                }
            )

        expected_data = [
            {
                'user_name': 'vansika',
                'artist_msid': 'a36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'artist_name': 'Less Than Jake',
                'listened_at': '2019-01-13 00:00:00',
                'recording_msid': 'cb6985cd-cc71-4d59-b4fb-2e72796af741',
                'release_msid': '',
                'release_name': 'lala',
                'track_name': "Al's War"
            },

            {
                'user_name': 'vansika',
                'artist_msid': 'f3e64219-ac00-4b6b-ad15-6e4801cb30a0',
                'artist_name': 'Townes Van Zandt',
                'listened_at': '2019-01-12 00:00:00',
                'recording_msid': '00000465-fcc1-41ab-a735-553f6ce677c4',
                'release_msid': '',
                'release_name': 'Sunshine Boy: The Unheard Studio Sessions & Demos 1971 - 1972',
                'track_name': 'Dead Flowers'
            }
        ]

        self.assertEqual(received_data, expected_data)

    def test_prepare_messages(self):
        partial_listen_df = create_dataframes.get_listens_for_training_model_window(self.date, self.date, {}, self.listens_path)
        mapping_df = utils.read_files_from_HDFS(self.mapping_path)
        from_date = datetime(2019, 6, 21)
        to_date = datetime(2019, 8, 21)
        ti = time.monotonic()

        itr = create_dataframes.get_data_missing_from_musicbrainz(partial_listen_df, mapping_df)

        messages = create_dataframes.prepare_messages(itr, from_date, to_date, ti)

        received_first_mssg = messages.pop(0)

        self.assertEqual(received_first_mssg['type'], 'cf_recording_dataframes')
        self.assertEqual(received_first_mssg['from_date'], str(from_date.strftime('%b %Y')))
        self.assertEqual(received_first_mssg['to_date'], str(to_date.strftime('%b %Y')))
        self.assertIsInstance(received_first_mssg['dataframe_upload_time'], str)
        self.assertIsInstance(received_first_mssg['total_time'], str)

        expected_missing_mb_data = [
            {
                'type': 'missing_musicbrainz_data',
                'musicbrainz_id': 'vansika',
                'missing_musicbrainz_data':
                    [
                        {
                            'artist_msid': 'a36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                            'artist_name': 'Less Than Jake',
                            'listened_at': '2019-01-13 00:00:00',
                            'recording_msid': 'cb6985cd-cc71-4d59-b4fb-2e72796af741',
                            'release_msid': '',
                            'release_name': 'lala',
                            'track_name': "Al's War"
                        },

                        {
                            'artist_msid': 'f3e64219-ac00-4b6b-ad15-6e4801cb30a0',
                            'artist_name': 'Townes Van Zandt',
                            'listened_at': '2019-01-12 00:00:00',
                            'recording_msid': '00000465-fcc1-41ab-a735-553f6ce677c4',
                            'release_msid': '',
                            'release_name': 'Sunshine Boy: The Unheard Studio Sessions & Demos 1971 - 1972',
                            'track_name': 'Dead Flowers'
                        }
                    ],
                'source': 'cf'
            }
        ]

        self.assertEqual(expected_missing_mb_data, messages)
