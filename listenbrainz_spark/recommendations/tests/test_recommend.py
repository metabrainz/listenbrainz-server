import os
from datetime import datetime

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import recommend
from listenbrainz_spark.recommendations import train_models
from listenbrainz_spark import schema, utils, config, path, stats

from pyspark.sql import Row
import pyspark.sql.functions as f

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

    def test_get_recommended_recordings(self):
        limit = 1
        candidate_set = self.get_candidate_set()
        recordings_df = self.get_recordings_df()
        mapped_listens = self.get_mapped_listens()
        model = recommend.load_model(config.HDFS_CLUSTER_URI + self.model_save_path)

        candidate_set_user = candidate_set.select('*') \
            .where(f.col('user_id') == 1)
        candidate_set_user_rdd = candidate_set_user.rdd.map(lambda r: (r['user_id'], r['recording_id']))
        recommended_rec = recommend.get_recommended_recordings(candidate_set_user_rdd, limit, recordings_df, model,
            mapped_listens)
        self.assertEqual(len(recommended_rec), limit)
        self.assertEqual(recommended_rec[0][0], "Al's War")
        self.assertEqual(recommended_rec[0][1], "Less Than Jake")
        self.assertEqual(recommended_rec[0][2], "3acb406f-c716-45f8-a8bd-96ca3939c2e5")
        self.assertEqual(recommended_rec[0][3], 1)

    def test_recommend_user(self):
        model = recommend.load_model(config.HDFS_CLUSTER_URI + self.model_save_path)
        recordings_df = self.get_recordings_df()
        users_df = self.get_users_df()
        top_artist_candidate_set = self.get_candidate_set()
        similar_artist_candidate_set = self.get_candidate_set()
        mapped_listens = self.get_mapped_listens()

        user_recommendations = recommend.recommend_user('vansika', model, recordings_df, users_df, top_artist_candidate_set,
            similar_artist_candidate_set, mapped_listens)
        self.assertLessEqual(len(user_recommendations['top_artists_recordings']), config.RECOMMENDATION_TOP_ARTIST_LIMIT)
        self.assertLessEqual(len(user_recommendations['similar_artists_recordings']),
            config.RECOMMENDATION_SIMILAR_ARTIST_LIMIT)

    def test_get_recommendations(self):
        model = recommend.load_model(config.HDFS_CLUSTER_URI + self.model_save_path)
        user_names = ['vansika', 'rob']
        recordings_df = self.get_recordings_df()
        users_df = self.get_users_df()
        top_artist_candidate_set = self.get_candidate_set()
        similar_artist_candidate_set = self.get_candidate_set()
        mapped_listens = self.get_mapped_listens()

        user_recommendations = recommend.get_recommendations(user_names, recordings_df, model, users_df,
            top_artist_candidate_set, similar_artist_candidate_set, mapped_listens)
        self.assertListEqual(user_recommendations['vansika'].get('top_artists_recordings'),
            [("Al's War", 'Less Than Jake', '3acb406f-c716-45f8-a8bd-96ca3939c2e5', 1)])
        self.assertListEqual(user_recommendations['vansika'].get('similar_artists_recordings'),
            [("Al's War", 'Less Than Jake', '3acb406f-c716-45f8-a8bd-96ca3939c2e5', 1)])
        self.assertTrue(user_recommendations['vansika'].get('time'))
        self.assertListEqual(user_recommendations['rob'].get('top_artists_recordings'),
            [('Mere Sapno ki Rani', 'Kishore Kumar', '2acb406f-c716-45f8-a8bd-96ca3939c2e5', 2)])
        self.assertListEqual(user_recommendations['rob'].get('similar_artists_recordings'),
            [('Mere Sapno ki Rani', 'Kishore Kumar', '2acb406f-c716-45f8-a8bd-96ca3939c2e5', 2)])
        self.assertTrue(user_recommendations['rob'].get('time'))
