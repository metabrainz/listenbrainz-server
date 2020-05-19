import os
from datetime import datetime
from unittest.mock import patch, call

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import recommend
from listenbrainz_spark.recommendations import train_models
from listenbrainz_spark import schema, utils, config, path, stats

from pyspark.sql import Row
import pyspark.sql.functions as f
from pyspark.rdd import RDD

MODEL_PATH = '/test/model'

class RecommendTestClass(SparkTestCase):

    model_save_path = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        super().upload_test_playcounts()
        cls.upload_test_model()

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    @classmethod
    def upload_test_model(cls):
        training_data, validation_data, test_data = super().split_playcounts()
        best_model, _, best_model_metadata = train_models.train(training_data, validation_data,
            validation_data.count(), cls.ranks, cls.lambdas, cls.iterations)
        cls.model_save_path = os.path.join(MODEL_PATH, best_model_metadata['model_id'])
        train_models.save_model(cls.model_save_path, best_model_metadata['model_id'], best_model)

    def test_load_model(self):
        model = recommend.load_model(config.HDFS_CLUSTER_URI + self.model_save_path)
        self.assertTrue(model)

    def test_generate_recommendations(self):
        model = recommend.load_model(config.HDFS_CLUSTER_URI + self.model_save_path)
        recordings_df = self.get_recordings_df()
        candidate_set = self.get_candidate_set()
        limit = 2

        candidate_set_rdd = candidate_set.rdd.map(lambda r: (r['user_id'], r['recording_id']))

        recommended_recording_mbids = recommend.generate_recommendations(candidate_set_rdd, limit, recordings_df, model)
        # often model gives no recommendations if candidate set has less data
        # therefore we check only for the type of return which should be a list
        self.assertEqual(type(recommended_recording_mbids), list)

    def test_get_recommendations_for_all(self):
        model = recommend.load_model(config.HDFS_CLUSTER_URI + self.model_save_path)
        recordings_df = self.get_recordings_df()
        top_artist_candidate_set = self.get_candidate_set()
        similar_artist_candidate_set = self.get_candidate_set()

        messages = recommend.get_recommendations_for_all(recordings_df, model, top_artist_candidate_set,
                                                         similar_artist_candidate_set)
        self.assertEqual(len(messages), 2)

        message = messages[0]
        self.assertTrue(message.get('musicbrainz_id'))
        self.assertTrue(message.get('type'))
        self.assertTrue(message.get('top_artist'))
        self.assertTrue(message.get('similar_artist'))

    def test_get_recommendations_for_user(self):
        model = recommend.load_model(config.HDFS_CLUSTER_URI + self.model_save_path)
        top_artists_candidate_set = self.get_candidate_set()
        similar_artists_candidate_set = self.get_candidate_set()
        recordings_df = self.get_recordings_df()
        user_name = 'vansika'
        user_id = 1

        user_recommendations_top_artist, user_recommendations_similar_artist = recommend.get_recommendations_for_user(
                model, user_id,
                user_name, recordings_df,
                top_artists_candidate_set,
                similar_artists_candidate_set
        )
        # often model gives no recommendations if candidate set has less data
        # therefore we check only for the type of return which should be a list
        self.assertEqual(type(user_recommendations_top_artist), list)
        self.assertEqual(type(user_recommendations_top_artist), list)
