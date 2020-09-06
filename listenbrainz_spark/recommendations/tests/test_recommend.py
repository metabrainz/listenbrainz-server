import os
import time
from datetime import datetime
import unittest
from unittest.mock import patch, call, MagicMock, Mock

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import recommend
from listenbrainz_spark.recommendations import train_models
from listenbrainz_spark import schema, utils, config, path, stats
from listenbrainz_spark.exceptions import (RecommendationsNotGeneratedException,
                                           EmptyDataframeExcpetion,
                                           RatingOutOfRangeException)

from pyspark.sql import Row
import pyspark.sql.functions as f
from pyspark.rdd import RDD
from pyspark.sql.functions import col
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
                user_id=1,
                recording_id=1,
                rating=0.313456
            ),
            schema=None
        )

        df = df.union(utils.create_dataframe(
            Row(
                user_id=1,
                recording_id=2,
                rating=6.994590001
            ),
            schema=None
        ))

        df = df.union(utils.create_dataframe(
            Row(
                user_id=2,
                recording_id=2,
                rating=-2.4587
            ),
            schema=None
        ))

        recommendation_df = df.union(utils.create_dataframe(
            Row(
                user_id=2,
                recording_id=1,
                rating=7.999
            ),
            schema=None
        ))

        return recommendation_df

    def test_get_recording_mbids(self):
        params = self.get_recommendation_params()
        recommendation_df = self.get_recommendation_df()
        users = []
        users_df = recommend.get_user_name_and_user_id(params, users)

        df = recommend.get_recording_mbids(params, recommendation_df, users_df)
        self.assertEqual(df.count(), 4)
        row = df.collect()

        self.assertEqual(row[0],
            Row(mb_recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                rank=1,
                rating=6.994590001,
                user_id=1,
                user_name='vansika')

        )

        self.assertEqual(row[1],
            Row(
                mb_recording_mbid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
                rank=2,
                rating=0.313456,
                user_id=1,
                user_name='vansika'
                )
        )

        self.assertEqual(row[2],
            Row(
                mb_recording_mbid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
                rank=1,
                rating=7.999,
                user_id=2,
                user_name='rob'
                )
        )

        self.assertEqual(row[3],
            Row(
                mb_recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                rank=2,
                rating=-2.4587,
                user_id=2,
                user_name='rob'
                )
        )


    def test_filter_recommendations_on_rating(self):
        df = self.get_recommendation_df()
        recommendation_df = df.select(col('user_id').alias('user'),
                                      col('recording_id').alias('product'),
                                      col('rating'))
        limit = 1

        df = recommend.filter_recommendations_on_rating(recommendation_df, limit)
        self.assertEqual(df.count(), 2)
        row = df.collect()

        self.assertEqual(row[0],
            Row(
                rating=6.994590001,
                recording_id=2,
                user_id=1)
        )

        self.assertEqual(row[1],
            Row(
                rating=7.999,
                recording_id=1,
                user_id=2)
        )

    @patch('listenbrainz_spark.recommendations.recommend.filter_recommendations_on_rating')
    @patch('listenbrainz_spark.recommendations.recommend.listenbrainz_spark')
    def test_generate_recommendations(self, mock_lb, mock_filter):
        params = self.get_recommendation_params()
        limit = 1

        mock_model = MagicMock()
        params.model = mock_model

        mock_predict = mock_model.predictAll
        candidate_set = self.get_candidate_set()
        users = []

        rdd = recommend.get_candidate_set_rdd_for_user(candidate_set, users)
        mock_predict.return_value = rdd

        df = recommend.generate_recommendations(candidate_set, params, limit)

        mock_predict.assert_called_once_with(candidate_set)

        mock_df = mock_lb.session.createDataFrame
        mock_df.assert_called_once_with(mock_predict.return_value, schema=None)

        mock_filter.assert_called_once_with(mock_df.return_value, limit)

        with self.assertRaises(RecommendationsNotGeneratedException):
            # empty rdd
            mock_predict.return_value = MagicMock()
            recommend.generate_recommendations(candidate_set, params, limit)

    def test_get_scale_rating_udf(self):
        rating = 1.6
        res = recommend.get_scale_rating_udf(rating)
        self.assertEqual(res, 1.0)

        rating = -1.6
        res = recommend.get_scale_rating_udf(rating)
        self.assertEqual(res, -0.3)

        rating = 0.65579
        res = recommend.get_scale_rating_udf(rating)
        self.assertEqual(res, 0.828)

        rating = -0.9999
        res = recommend.get_scale_rating_udf(rating)
        self.assertEqual(res, 0.0)

    def test_scale_rating(self):
        df = self.get_recommendation_df()

        df = recommend.scale_rating(df)
        self.assertEqual(sorted(df.columns), ['rating', 'recording_id', 'user_id'])
        received_ratings = sorted([row.rating for row in df.collect()])
        expected_ratings = [-0.729, 0.657, 1.0, 1.0]

    def test_get_candidate_set_rdd_for_user(self):
        candidate_set = self.get_candidate_set()
        users = []

        candidate_set_rdd = recommend.get_candidate_set_rdd_for_user(candidate_set, users)
        self.assertTrue(isinstance(candidate_set_rdd, RDD))
        res = sorted([row for row in candidate_set_rdd.collect()])
        self.assertEqual(res, [(1, 1), (2, 2)])

        users = ['vansika']
        candidate_set_rdd = recommend.get_candidate_set_rdd_for_user(candidate_set, users)

        self.assertTrue(isinstance(candidate_set_rdd, RDD))
        row = candidate_set_rdd.collect()
        self.assertEqual([(1, 1)], row)

        users = ['vansika_1']
        with self.assertRaises(EmptyDataframeExcpetion):
            recommend.get_candidate_set_rdd_for_user(candidate_set, users)

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

        users = []
        users_df = recommend.get_user_name_and_user_id(params, [])

        self.assertEqual(users_df.count(), 2)
        user_name = sorted([row.user_name for row in users_df.collect()])
        user_id = sorted([row.user_id for row in users_df.collect()])
        self.assertEqual(sorted(users_df.columns), sorted(['user_id', 'user_name']))
        self.assertEqual(['rob', 'vansika'], user_name)
        self.assertEqual([1, 2], user_id)

        users = ['vansika', 'invalid']
        users_df = recommend.get_user_name_and_user_id(params, users)
        self.assertEqual(users_df.count(), 1)
        self.assertEqual(sorted(users_df.columns), sorted(['user_id', 'user_name']))
        user_name = [row.user_name for row in users_df.collect()]
        user_id = [row.user_id for row in users_df.collect()]
        self.assertEqual(['vansika'], user_name)
        self.assertEqual([1], user_id)

        with self.assertRaises(EmptyDataframeExcpetion):
            users = ['invalid']
            recommend.get_user_name_and_user_id(params, users)

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

    @patch('listenbrainz_spark.recommendations.recommend.get_candidate_set_rdd_for_user')
    @patch('listenbrainz_spark.recommendations.recommend.get_recommended_mbids')
    def test_get_recommendations_for_user(self, mock_mbids, mock_candidate_set):
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

        user_name = 'vansika_1'
        mock_candidate_set.side_effect = IndexError
        recommend.get_recommendations_for_user(user_id, user_name, params)
        self.assertEqual(params.top_artist_not_found, ['vansika_1'])
        self.assertEqual(params.similar_artist_not_found, ['vansika_1'])

        user_name = 'vansika_2'
        mock_candidate_set.side_effect = RecommendationsNotGeneratedException(message='Recommendations not generated')
        recommend.get_recommendations_for_user(user_id, user_name, params)
        self.assertEqual(params.top_artist_rec_not_generated, ['vansika_2'])
        self.assertEqual(params.similar_artist_rec_not_generated, ['vansika_2'])

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
