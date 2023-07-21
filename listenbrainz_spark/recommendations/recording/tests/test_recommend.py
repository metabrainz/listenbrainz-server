import logging
import uuid
from unittest.mock import patch, MagicMock

from pyspark.sql import Row
from pyspark.sql.types import StructType

import listenbrainz_spark
from listenbrainz_spark import schema, utils, path
from listenbrainz_spark.exceptions import (RecommendationsNotGeneratedException,
                                           EmptyDataframeExcpetion)
from listenbrainz_spark.recommendations.recording import recommend
from listenbrainz_spark.recommendations.recording.tests import RecommendationsTestCase
# for test data/dataframes refer to listenbrainzspark/tests/__init__.py
from listenbrainz_spark.schema import recommendation_schema

logger = logging.getLogger(__name__)


class RecommendTestClass(RecommendationsTestCase):

    def test_process_recommendations(self):
        recommendation_df = listenbrainz_spark.session.createDataFrame([
            Row(spark_user_id=1, recording_id=1, prediction=0.5),
            Row(spark_user_id=1, recording_id=2, prediction=-0.5),
            Row(spark_user_id=2, recording_id=2, prediction=1.0),
            Row(spark_user_id=2, recording_id=1, prediction=0.25),
            Row(spark_user_id=2, recording_id=3, prediction=0.75),
        ])

        recording_df = listenbrainz_spark.session.createDataFrame([
            Row(recording_mbid="3acb406f-c716-45f8-a8bd-96ca3939c2e5", recording_id=1),
            Row(recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5", recording_id=2),
            Row(recording_mbid="8acb406f-c716-45f8-a8bd-96ca3939c2e5", recording_id=3)
        ])
        discovery_df = listenbrainz_spark.session.createDataFrame([
            Row(
                user_id=1,
                recording_mbid="8acb406f-c716-45f8-a8bd-96ca3939c2e5",
                latest_listened_at="2020-11-14T06:21:02.000Z"
            ),
            Row(
                user_id=1,
                recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                latest_listened_at="2021-12-17T05:32:11.000Z"
            ),
            Row(
                user_id=3,
                recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                latest_listened_at="2019-10-12T09:43:57.000Z"
            )
        ])
        user_df = listenbrainz_spark.session.createDataFrame([
            Row(spark_user_id=1, user_id=3),
            Row(spark_user_id=2, user_id=1)
        ])

        recording_df.createOrReplaceTempView("recording")
        discovery_df.createOrReplaceTempView("recording_discovery")
        user_df.createOrReplaceTempView("user")

        recommendations = recommend.process_recommendations(recommendation_df, 2)
        self.assertEqual(recommendations.count(), 2)

        # Each user's rows are ordered by scores but the order of users is not
        # fixed so need to test each user's recommendations separately.

        rows_user_1 = recommendations.where(recommendations.user_id == 1).collect()[0]
        self.assertEqual(
            rows_user_1,
            Row(user_id=1, recs=[
                Row(
                    recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                    score=1.0,
                    latest_listened_at="2021-12-17T05:32:11.000Z"
                ),
                Row(
                    recording_mbid="8acb406f-c716-45f8-a8bd-96ca3939c2e5",
                    score=0.75,
                    latest_listened_at="2020-11-14T06:21:02.000Z"
                )
            ])
        )

        rows_user_3 = recommendations.where(recommendations.user_id == 3).collect()[0]
        self.assertEqual(
            rows_user_3,
            Row(user_id=3, recs=[
                Row(
                    recording_mbid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
                    score=0.5,
                    latest_listened_at=None
                ),
                Row(
                    recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                    score=-0.5,
                    latest_listened_at="2019-10-12T09:43:57.000Z"
                )
            ])
        )

    @patch('listenbrainz_spark.recommendations.recording.recommend.process_recommendations')
    @patch('listenbrainz_spark.recommendations.recording.recommend.listenbrainz_spark')
    def test_generate_recommendations(self, mock_lb, mock_process):
        limit = 1
        mock_model = MagicMock()
        mock_predict = mock_model.transform
        candidate_set = self.get_candidate_set()
        users = []

        rdd = recommend.get_candidate_set_rdd_for_user(candidate_set, users)
        mock_predict.return_value = rdd

        recommend.generate_recommendations(candidate_set, mock_model, limit)
        mock_predict.assert_called_once_with(candidate_set)
        mock_process.assert_called_once_with(mock_predict.return_value, limit)

        with self.assertRaises(RecommendationsNotGeneratedException):
            # empty rdd
            mock_predict.return_value = listenbrainz_spark.session.createDataFrame([], schema=StructType([]))
            recommend.generate_recommendations(candidate_set, mock_model, limit)

    def test_get_candidate_set_rdd_for_user(self):
        candidate_set = self.get_candidate_set()
        users = []

        candidate_set_rdd = recommend.get_candidate_set_rdd_for_user(candidate_set, users)
        res = sorted([row for row in candidate_set_rdd.collect()])
        self.assertEqual(res, [(1, 1), (2, 2)])

        users = [3]
        candidate_set_rdd = recommend.get_candidate_set_rdd_for_user(candidate_set, users)

        row = candidate_set_rdd.collect()
        self.assertEqual([(1, 1)], row)

        users = [4]
        with self.assertRaises(EmptyDataframeExcpetion):
            recommend.get_candidate_set_rdd_for_user(candidate_set, users)

    def test_get_user_name_and_user_id(self):
        df = listenbrainz_spark.session.createDataFrame([
            Row(spark_user_id=1, user_id=3, recording_id=1),
            Row(spark_user_id=1, user_id=3, recording_id=2),
            Row(spark_user_id=2, user_id=1, recording_id=1),
        ], schema=None)

        users_df = recommend.get_user_name_and_user_id(df, [])
        self.assertEqual(users_df.count(), 2)
        user_id = sorted([row.user_id for row in users_df.collect()])
        spark_user_id = sorted([row.spark_user_id for row in users_df.collect()])
        self.assertEqual(sorted(users_df.columns), sorted(['spark_user_id', 'user_id']))
        self.assertEqual([1, 3], user_id)
        self.assertEqual([1, 2], spark_user_id)

        users = [3, 100]
        users_df = recommend.get_user_name_and_user_id(df, users)
        self.assertEqual(users_df.count(), 1)
        self.assertEqual(sorted(users_df.columns), sorted(['spark_user_id', 'user_id']))
        user_id = [row.user_id for row in users_df.collect()]
        spark_user_id = [row.spark_user_id for row in users_df.collect()]
        self.assertEqual([3], user_id)
        self.assertEqual([1], spark_user_id)

        with self.assertRaises(EmptyDataframeExcpetion):
            users = ['invalid']
            recommend.get_user_name_and_user_id(df, users)

    @patch('listenbrainz_spark.recommendations.recording.recommend.ALSModel')
    @patch('listenbrainz_spark.recommendations.recording.recommend.get_model_path')
    def test_load_model(self, mock_model_path, mock_als_model):
        model_id = uuid.uuid4()
        recommend.load_model(model_id)
        mock_model_path.assert_called_once_with(model_id)
        mock_als_model.load.assert_called_once_with(mock_model_path.return_value)

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
        utils.save_parquet(model_metadata, path.RECOMMENDATION_RECORDING_MODEL_METADATA)

        expected_model_meta = recommend.get_most_recent_model_meta()
        self.assertEqual(expected_model_meta[0], model_id_2)
        self.assertEqual(expected_model_meta[1], f"{model_id_2}.html")

    def get_raw_rec_df(self):
        return listenbrainz_spark.session.createDataFrame([
            Row(user_id=4, recs=[
                Row(
                    latest_listened_at=None,
                    recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                    score=4.0
                )
            ]),
            Row(user_id=3, recs=[
                Row(
                    latest_listened_at="2019-10-12T09:43:57.000Z",
                    recording_mbid="8acb406f-c716-45f8-a8bd-96ca3939c2e5",
                    score=-1.0,
                )
            ])
        ], schema=recommendation_schema)

    def test_create_messages(self):
        self.maxDiff = None
        model_id = "foobar"
        model_html_file = "foobar.html"
        raw_rec_df = self.get_raw_rec_df()
        active_user_count = 10
        raw_rec_user_count = 2
        total_time = 3600

        data = recommend.create_messages(model_id, model_html_file, raw_rec_df, active_user_count, total_time)
        self.assertCountEqual(list(data), [
            {
                'user_id': 3,
                'type': 'cf_recommendations_recording_recommendations',
                'recommendations': {
                    'raw': [
                        {
                            'latest_listened_at': '2019-10-12T09:43:57.000Z',
                            'recording_mbid': '8acb406f-c716-45f8-a8bd-96ca3939c2e5',
                            'score': -1.0
                        }
                    ],
                    'model_id': 'foobar',
                    'model_url': 'http://michael.metabrainz.org/foobar.html'
                }
            },
            {
                'user_id': 4,
                'type': 'cf_recommendations_recording_recommendations',
                'recommendations': {
                    'raw': [
                        {
                            'recording_mbid': "2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                            'score': 4.0,
                            'latest_listened_at': None
                        }
                    ],
                    'model_id': 'foobar',
                    'model_url': 'http://michael.metabrainz.org/foobar.html'
                }
            },
            {
                'type': 'cf_recommendations_recording_mail',
                'active_user_count': active_user_count,
                'raw_rec_user_count': raw_rec_user_count,
                'total_time': '1.00'
            }
        ])

    def test_get_user_count(self):
        df = listenbrainz_spark.session.createDataFrame(
            [Row(user_id=3), Row(user_id=3), Row(user_id=2)], schema=None
        )
        user_count = recommend.get_user_count(df)
        self.assertEqual(user_count, 2)
