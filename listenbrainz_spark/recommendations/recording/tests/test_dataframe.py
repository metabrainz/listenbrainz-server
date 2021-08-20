import json
import unittest
from datetime import datetime

import os

import listenbrainz_spark
import listenbrainz_spark.utils.mapping as mapping_utils
from listenbrainz_spark.path import LISTENBRAINZ_NEW_DATA_DIRECTORY, RECOMMENDATION_RECORDING_MAPPED_LISTENS, \
    RECOMMENDATION_RECORDINGS_DATAFRAME, RECOMMENDATION_RECORDING_USERS_DATAFRAME, \
    RECOMMENDATION_RECORDING_PLAYCOUNTS_DATAFRAME, RECOMMENDATION_RECORDING_DATAFRAME_METADATA
from listenbrainz_spark.recommendations.recording.tests import RecommendationsTestCase
from listenbrainz_spark.tests import SparkTestCase, SparkNewTestCase, TEST_DATA_PATH
from listenbrainz_spark.recommendations.recording import create_dataframes
from listenbrainz_spark.utils import get_latest_listen_ts, get_listens_from_new_dump
from listenbrainz_spark import schema, utils, config, path, hdfs_connection, stats

from pyspark.sql import Row
import time


class CreateDataframeTestCase(RecommendationsTestCase):

    @classmethod
    def setUpClass(cls):
        super(CreateDataframeTestCase, cls).setUpClass()
        # upload testdata/rec_listens.parquet to HDFS
        utils.upload_to_HDFS(LISTENBRAINZ_NEW_DATA_DIRECTORY, os.path.join(TEST_DATA_PATH, 'rec_listens.parquet'))
        utils.upload_to_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS, os.path.join(TEST_DATA_PATH, 'mapped_listens.parquet'))

    @classmethod
    def tearDownClass(cls):
        super(CreateDataframeTestCase, cls).tearDownClass()
        cls.delete_uploaded_listens()
        if utils.path_exists(RECOMMENDATION_RECORDING_MAPPED_LISTENS):
            utils.delete_dir(RECOMMENDATION_RECORDING_MAPPED_LISTENS, recursive=True)

    def test_get_users_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, metadata, RECOMMENDATION_RECORDING_USERS_DATAFRAME)
        self.assertEqual(users_df.count(), 2)

        expected_users_df = listenbrainz_spark.session.createDataFrame([
            Row(user_name='amCap1712', user_id=1),
            Row(user_name='rob', user_id=2)
        ])
        self.assertListEqual(list(expected_users_df.toLocalIterator()), list(users_df.toLocalIterator()))
        self.assertCountEqual(expected_users_df.columns, users_df.columns)
        self.assertEqual(metadata['users_count'], 2)

        status = utils.path_exists(RECOMMENDATION_RECORDING_USERS_DATAFRAME)
        self.assertTrue(status)

    def test_get_recordings_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, metadata, RECOMMENDATION_RECORDINGS_DATAFRAME)
        self.assertEqual(recordings_df.count(), 20)
        self.assertCountEqual(['artist_credit_id', 'recording_id', 'recording_mbid'], recordings_df.columns)
        self.assertEqual(metadata['recordings_count'], 20)

        status = utils.path_exists(RECOMMENDATION_RECORDINGS_DATAFRAME)
        self.assertTrue(status)

    def test_get_listens_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        listens_df = create_dataframes.get_listens_df(mapped_listens, metadata)
        self.assertEqual(listens_df.count(), 24)
        self.assertCountEqual(['recording_mbid', 'user_name'], listens_df.columns)
        self.assertEqual(metadata['listens_count'], 24)

    def test_save_playcounts_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, {}, RECOMMENDATION_RECORDING_USERS_DATAFRAME)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, {}, RECOMMENDATION_RECORDINGS_DATAFRAME)
        listens_df = create_dataframes.get_listens_df(mapped_listens, {})

        create_dataframes.save_playcounts_df(listens_df, recordings_df, users_df, metadata, RECOMMENDATION_RECORDING_PLAYCOUNTS_DATAFRAME)
        playcounts_df = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_PLAYCOUNTS_DATAFRAME)
        self.assertEqual(playcounts_df.count(), 20)

        self.assertListEqual(['user_id', 'recording_id', 'count'], playcounts_df.columns)
        self.assertEqual(metadata['playcounts_count'], 20)

    def test_save_dataframe_metadata_to_HDFS(self):
        df_id = "3acb406f-c716-45f8-a8bd-96ca3939c2e5"
        metadata = self.get_dataframe_metadata(df_id)
        create_dataframes.save_dataframe_metadata_to_hdfs(metadata, RECOMMENDATION_RECORDING_DATAFRAME_METADATA)

        status = utils.path_exists(RECOMMENDATION_RECORDING_DATAFRAME_METADATA)
        self.assertTrue(status)

        df = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_DATAFRAME_METADATA)
        self.assertCountEqual(df.columns, schema.dataframe_metadata_schema.fieldNames())

    def test_get_data_missing_from_musicbrainz(self):
        partial_listen_df = utils.read_files_from_HDFS(LISTENBRAINZ_NEW_DATA_DIRECTORY)
        itr = create_dataframes.get_data_missing_from_musicbrainz(partial_listen_df)
        messages = create_dataframes.prepare_messages(itr, self.begin_date, self.end_date, time.monotonic())

        received_first_mssg = messages.pop(0)

        self.assertEqual(received_first_mssg['type'], 'cf_recommendations_recording_dataframes')
        self.assertEqual(received_first_mssg['from_date'], str(self.begin_date.strftime('%b %Y')))
        self.assertEqual(received_first_mssg['to_date'], str(self.end_date.strftime('%b %Y')))
        self.assertIsInstance(received_first_mssg['dataframe_upload_time'], str)
        self.assertIsInstance(received_first_mssg['total_time'], str)

        with open(os.path.join(TEST_DATA_PATH, 'missing_musicbrainz_data.json')) as f:
            expected_missing_mb_data = json.load(f)
        self.assertEqual(expected_missing_mb_data, messages)
