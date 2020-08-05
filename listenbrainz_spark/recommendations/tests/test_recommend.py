import os
from datetime import datetime
from unittest.mock import patch, call, MagicMock

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import recommend
from listenbrainz_spark.recommendations import train_models
from listenbrainz_spark import schema, utils, config, path, stats
from listenbrainz_spark.exceptions import RecommendationsNotGeneratedException

from pyspark.sql import Row
import pyspark.sql.functions as f
from pyspark.rdd import RDD
from pyspark.mllib.recommendation import Rating

# for test data/dataframes refer to listenbrainzspark/tests/__init__.py

class RecommendTestClass(SparkTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    def test_recommendation_params_init(self):
        recordings_df = utils.create_dataframe(Row(col1=3, col2=9), schema=None)
        model = MagicMock()
        top_artist_candidate_set_df = utils.create_dataframe(Row(col1=4, col2=5, col3=5), schema=None)
        similar_artist_candidate_set_df = utils.create_dataframe(Row(col1=1), schema=None)
        recommendation_top_artist_limit = 20
        recommendation_similar_artist_limit = 40

        params = recommend.RecommendationParams(recordings_df, model, top_artist_candidate_set_df,
                                                similar_artist_candidate_set_df,
                                                recommendation_top_artist_limit,
                                                recommendation_similar_artist_limit)

        self.assertEqual(sorted(params.recordings_df.columns), sorted(recordings_df.columns))
        self.assertEqual(params.model, model)
        self.assertEqual(sorted(params.top_artist_candidate_set_df.columns), sorted(top_artist_candidate_set_df.columns))
        self.assertEqual(sorted(params.similar_artist_candidate_set_df.columns), sorted(similar_artist_candidate_set_df.columns))
        self.assertEqual(params.recommendation_top_artist_limit, recommendation_top_artist_limit)
        self.assertEqual(params.recommendation_similar_artist_limit, recommendation_similar_artist_limit)

    def get_recommendation_df(self):
        df = utils.create_dataframe(
            Row(
                recording_id=1,
                rating=3.13456
            ),
            schema=None
        )

        recommendation_df = df.union(utils.create_dataframe(
            Row(
                recording_id=2,
                rating=6.994590001
            ),
            schema=None
        ))

        return recommendation_df

    def test_get_recording_mbids(self):
        params = self.get_recommendation_params()
        recommendation_df = self.get_recommendation_df()

        recording_mbids = recommend.get_recording_mbids(params, recommendation_df)

        self.assertEqual(recording_mbids.count(), 2)
        self.assertEqual(sorted(recording_mbids.columns), sorted(["mb_recording_mbid", "rating"]))
        self.assertEqual(recording_mbids.collect()[0].mb_recording_mbid, "2acb406f-c716-45f8-a8bd-96ca3939c2e5")
        self.assertEqual(recording_mbids.collect()[1].mb_recording_mbid, "3acb406f-c716-45f8-a8bd-96ca3939c2e5")

    def test_get_recommendation_df(self):
        recording_ids_and_ratings = [[1, 3.1], [2, 6.0]]

        df = recommend.get_recommendation_df(recording_ids_and_ratings)

        self.assertEqual(sorted(df.columns), ['rating', 'recording_id'])

        row = df.collect()
        self.assertEqual(row[0][0], 1)
        self.assertEqual(round(row[0][1], 1), 3.1)
        self.assertEqual(row[1][0], 2)
        self.assertEqual(round(row[1][1], 1), 6.0)

    @patch('listenbrainz_spark.recommendations.recommend.MatrixFactorizationModel')
    @patch('listenbrainz_spark.recommendations.recommend.listenbrainz_spark')
    @patch('listenbrainz_spark.recommendations.recommend.get_model_path')
    @patch('listenbrainz_spark.recommendations.recommend.get_most_recent_model_id')
    def test_load_model(self, mock_id, mock_model_path, mock_lb, mock_matrix_model):
        model = recommend.load_model()
        mock_id.assert_called_once()
        mock_model_path.assert_called_once_with(mock_id.return_value)
        mock_matrix_model.load.assert_called_once_with(mock_lb.context, mock_model_path.return_value)

    def test_get_most_recent_model_id(self):
        model_id_1 = "a36d6fc9-49d0-4789-a7dd-a2b72369ca45"
        model_metadata_dict_1 = self.get_model_metadata(model_id_1)
        df_1 = utils.create_dataframe(schema.convert_model_metadata_to_row(model_metadata_dict_1),
                                      schema.model_metadata_schema)

        model_id_2 = "bbbd6fc9-49d0-4789-a7dd-a2b72369ca45"
        model_metadata_dict_2 = self.get_model_metadata(model_id_2)
        df_2 = utils.create_dataframe(schema.convert_model_metadata_to_row(model_metadata_dict_2),
                                      schema.model_metadata_schema)

        model_metadata = df_1.union(df_2)
        utils.save_parquet(model_metadata, path.MODEL_METADATA)

        expected_model_id = recommend.get_most_recent_model_id()
        self.assertEqual(expected_model_id, model_id_2)

    def test_generate_recommendations(self):
        params = self.get_recommendation_params()
        limit = 1
        mock_candidate_set = MagicMock()

        mock_model = MagicMock()
        params.model = mock_model

        _ = recommend.generate_recommendations(mock_candidate_set, params, limit)

        mock_predict = mock_model.predictAll
        mock_predict.assert_called_once_with(mock_candidate_set)

        mock_take_ordered = mock_predict.return_value.takeOrdered
        self.assertEqual(mock_take_ordered.call_args[0][0], limit)

    def test_get_candidate_set_rdd_for_user(self):
        candidate_set = self.get_candidate_set()
        user_id = 1

        candidate_set_rdd = recommend.get_candidate_set_rdd_for_user(candidate_set, user_id)

        self.assertTrue(isinstance(candidate_set_rdd, RDD))
        self.assertEqual(candidate_set_rdd.collect()[0][0], user_id)
        self.assertEqual(candidate_set_rdd.collect()[0][1], 1)

        user_id = 10
        with self.assertRaises(IndexError):
            candidate_set_rdd = recommend.get_candidate_set_rdd_for_user(candidate_set, user_id)

    @patch('listenbrainz_spark.recommendations.recommend.get_recommended_mbids')
    @patch('listenbrainz_spark.recommendations.recommend.get_candidate_set_rdd_for_user')
    def test_get_recommendations_for_user(self, mock_candidate_set, mock_mbids):
        params = self.get_recommendation_params()
        user_id = 1
        user_name = 'vansika'

        _, _ = recommend.get_recommendations_for_user(user_id, user_name, params)

        mock_candidate_set.assert_has_calls([
            call(params.top_artist_candidate_set_df, user_id),
            call(params.similar_artist_candidate_set_df, user_id)
        ])

        mock_mbids.assert_has_calls([
            call(mock_candidate_set.return_value, params, params.recommendation_top_artist_limit),
            call(mock_candidate_set.return_value, params, params.recommendation_similar_artist_limit)
        ])


    @patch('listenbrainz_spark.recommendations.recommend.generate_recommendations')
    def test_get_recommended_mbids(self, mock_gen_rec):
        candidate_set = self.get_candidate_set()
        params = self.get_recommendation_params()
        limit = 2

        rdd = candidate_set.rdd.map(lambda r: (r['user_id'], r['recording_id']))
        mock_gen_rec.return_value = [
            Rating(user=2, product=1, rating=3.13456),
            Rating(user=2, product=2, rating=6.994590001)
        ]

        recommended_mbids = recommend.get_recommended_mbids(rdd, params, limit)

        mock_gen_rec.assert_called_once_with(rdd, params, limit)
        self.assertEqual(recommended_mbids[0][0], '2acb406f-c716-45f8-a8bd-96ca3939c2e5')
        self.assertEqual(recommended_mbids[0][1], 6.995)
        self.assertEqual(recommended_mbids[1][0], '3acb406f-c716-45f8-a8bd-96ca3939c2e5')
        self.assertEqual(recommended_mbids[1][1], 3.135)

        mock_gen_rec.return_value = []
        with self.assertRaises(RecommendationsNotGeneratedException):
            _ = recommend.get_recommended_mbids(rdd, params, limit)

    def test_get_user_name_and_user_id(self):
        params = self.get_recommendation_params()
        df = utils.create_dataframe(
            Row(
                user_id=1,
                user_name='vansika',
                recording_id=1
            ),
            schema=None
        )

        df = df.union(utils.create_dataframe(
            Row(
                user_id=1,
                user_name='vansika',
                recording_id=2
            ),
            schema=None
        ))

        df = df.union(utils.create_dataframe(
            Row(
                user_id=2,
                user_name='rob',
                recording_id=1
            ),
            schema=None
        ))

        params.top_artist_candidate_set_df = df

        users = recommend.get_user_name_and_user_id(params, [])

        self.assertEqual(users.count(), 2)
        self.assertEqual(sorted(users.columns), sorted(['user_id', 'user_name']))

        users = recommend.get_user_name_and_user_id(params, ['vansika'])
        self.assertEqual(users.count(), 1)
        self.assertEqual(sorted(users.columns), sorted(['user_id', 'user_name']))

    def test_get_message_for_inactive_users(self):
        message_arg = [{
            'musicbrainz_id': 'vansika',
            'type': 'cf_recording_recommendations',
            'top_artist': ["181c4177-f33a-441d-b15d-910acaf18b07"],
            'similar_artist': ["281c4177-f33a-441d-b15d-910acaf18b07"],
        }]

        active_users = ['vansika']
        users = ['vansika', 'vansika_1']
        messages = recommend.get_message_for_inactive_users(message_arg, active_users, users)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], message_arg[0])
        self.assertEqual(messages[1], {
            'musicbrainz_id': 'vansika_1',
            'type': 'cf_recording_recommendations',
            'top_artist': [],
            'similar_artist': [],
        })

    @patch('listenbrainz_spark.recommendations.recommend.get_recommendations_for_user')
    def test_get_recommendations_for_all_without_users(self, mock_rec_user):
        params = self.get_recommendation_params()
        df = utils.create_dataframe(
            Row(
                user_id=1,
                user_name='vansika',
                recording_id=1
            ),
            schema=None
        )
        params.top_artist_candidate_set_df = df

        mock_rec_user.return_value = 'recording_mbid_1', 'recording_mbid_2'
        messages = recommend.get_recommendations_for_all(params, [])
        mock_rec_user.assert_called_once_with(1, 'vansika', params)

        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertEqual(message['musicbrainz_id'], 'vansika')
        self.assertEqual(message['type'], 'cf_recording_recommendations')
        self.assertEqual(message['top_artist'], 'recording_mbid_1')
        self.assertEqual(message['similar_artist'], 'recording_mbid_2')

    @patch('listenbrainz_spark.recommendations.recommend.get_recommendations_for_user')
    def test_get_recommendations_for_all_with_users(self, mock_rec_user):
        params = self.get_recommendation_params()
        df = utils.create_dataframe(
            Row(
                user_id=1,
                user_name='vansika',
                recording_id=1
            ),
            schema=None
        )
        params.top_artist_candidate_set = df
        mock_rec_user.return_value = 'recording_mbid_3', 'recording_mbid_4'
        messages = recommend.get_recommendations_for_all(params, ['vansika_1', 'vansika'])
        mock_rec_user.assert_called_once_with(1, 'vansika', params)

        self.assertEqual(len(messages), 2)

        message = messages[0]
        self.assertEqual(message['musicbrainz_id'], 'vansika')
        self.assertEqual(message['type'], 'cf_recording_recommendations')
        self.assertEqual(message['top_artist'], 'recording_mbid_3')
        self.assertEqual(message['similar_artist'], 'recording_mbid_4')

        message = messages[1]
        self.assertEqual(message['musicbrainz_id'], 'vansika_1')
        self.assertEqual(message['type'], 'cf_recording_recommendations')
        self.assertEqual(message['top_artist'], [])
        self.assertEqual(message['similar_artist'], [])

    def get_recommendation_params(self):
        recordings_df = self.get_recordings_df()
        model = MagicMock()
        top_artist_candidate_set_df = self.get_candidate_set()
        similar_artist_candidate_set_df = self.get_candidate_set()
        recommendation_top_artist_limit = 2
        recommendation_similar_artist_limit = 1

        params = recommend.RecommendationParams(recordings_df, model, top_artist_candidate_set_df,
                                                similar_artist_candidate_set_df,
                                                recommendation_top_artist_limit,
                                                recommendation_similar_artist_limit)
        return params
