from pyspark.sql import Row

import listenbrainz_spark
from listenbrainz_spark import schema, utils
from listenbrainz_spark.path import RECOMMENDATION_RECORDING_MAPPED_LISTENS, \
    RECOMMENDATION_RECORDINGS_DATAFRAME, RECOMMENDATION_RECORDING_USERS_DATAFRAME, \
    RECOMMENDATION_RECORDING_TRANSFORMED_LISTENCOUNTS_DATAFRAME, RECOMMENDATION_RECORDING_DATAFRAME_METADATA
from listenbrainz_spark.recommendations.recording import create_dataframes
from listenbrainz_spark.recommendations.recording.tests import RecommendationsTestCase
from listenbrainz_spark.hdfs.utils import path_exists

class CreateDataframeTestCase(RecommendationsTestCase):

    def test_get_users_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, metadata, RECOMMENDATION_RECORDING_USERS_DATAFRAME)
        self.assertEqual(users_df.count(), 2)

        expected_users_df = listenbrainz_spark.session.createDataFrame([
            Row(user_id=1, spark_user_id=1),
            Row(user_id=2, spark_user_id=2)
        ])
        self.assertListEqual(list(expected_users_df.toLocalIterator()), list(users_df.toLocalIterator()))
        self.assertCountEqual(expected_users_df.columns, users_df.columns)
        self.assertEqual(metadata['users_count'], 2)

        status = path_exists(RECOMMENDATION_RECORDING_USERS_DATAFRAME)
        self.assertTrue(status)

    def test_get_recordings_dataframe(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, metadata, RECOMMENDATION_RECORDINGS_DATAFRAME)
        self.assertEqual(recordings_df.count(), 20)
        self.assertCountEqual(['artist_credit_id', 'recording_id', 'recording_mbid'], recordings_df.columns)
        self.assertEqual(metadata['recordings_count'], 20)

        status = path_exists(RECOMMENDATION_RECORDINGS_DATAFRAME)
        self.assertTrue(status)

    def test_get_listens_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        listens_df = create_dataframes.get_listens_df(mapped_listens, metadata)
        self.assertEqual(listens_df.count(), 24)
        self.assertCountEqual(['recording_mbid', 'user_id'], listens_df.columns)
        self.assertEqual(metadata['listens_count'], 24)

    def test_save_playcounts_df(self):
        metadata = {}
        mapped_listens = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        users_df = create_dataframes.get_users_dataframe(mapped_listens, {}, RECOMMENDATION_RECORDING_USERS_DATAFRAME)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens, {}, RECOMMENDATION_RECORDINGS_DATAFRAME)
        listens_df = create_dataframes.get_listens_df(mapped_listens, {})

        create_dataframes.save_playcounts_df(listens_df, recordings_df, users_df, metadata, RECOMMENDATION_RECORDING_TRANSFORMED_LISTENCOUNTS_DATAFRAME)
        playcounts_df = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_TRANSFORMED_LISTENCOUNTS_DATAFRAME)
        self.assertEqual(playcounts_df.count(), 20)

        self.assertListEqual(['spark_user_id', 'recording_id', 'playcount', 'transformed_listencount'], playcounts_df.columns)
        self.assertEqual(metadata['playcounts_count'], 20)

    def test_save_dataframe_metadata_to_HDFS(self):
        df_id = "3acb406f-c716-45f8-a8bd-96ca3939c2e5"
        metadata = self.get_dataframe_metadata(df_id)
        create_dataframes.save_dataframe_metadata_to_hdfs(metadata, RECOMMENDATION_RECORDING_DATAFRAME_METADATA)

        status = path_exists(RECOMMENDATION_RECORDING_DATAFRAME_METADATA)
        self.assertTrue(status)

        df = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_DATAFRAME_METADATA)
        self.assertCountEqual(df.columns, schema.dataframe_metadata_schema.fieldNames())
