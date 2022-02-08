# The tests here use a listens dataset different from other tests, hence they are isolated here to avoid
# future confusion. The reason for a separate dataset is that to test some methods, we want multiple
# recordings from a `top artist` for the user. Some of these recordings should not have been listened
# during recommendation generation window otherwise we'll just get empty candidate sets.
import os
import pytest
from datetime import datetime, timezone

from pyspark import Row

import listenbrainz_spark
from listenbrainz_spark import stats
from listenbrainz_spark.path import RECOMMENDATION_RECORDINGS_DATAFRAME, RECOMMENDATION_RECORDING_USERS_DATAFRAME
from listenbrainz_spark.recommendations.recording import candidate_sets, create_dataframes
from listenbrainz_spark.tests import SparkNewTestCase, TEST_DATA_PATH


class CandidateSetsTestClass(SparkNewTestCase):

    @classmethod
    def setUpClass(cls):
        super(CandidateSetsTestClass, cls).setUpClass()
        cls.mapped_listens_df = listenbrainz_spark \
            .session \
            .read \
            .parquet("file://" + os.path.join(TEST_DATA_PATH, 'mapped_listens_candidate_sets.parquet')) \
            .where("recording_mbid IS NOT NULL")

        to_date = datetime(2019, 1, 21, tzinfo=timezone.utc)
        from_date = stats.offset_days(to_date, 4)

        cls.mapped_listens_subset = candidate_sets.get_listens_to_fetch_top_artists(
            cls.mapped_listens_df, from_date, to_date
        )

        cls.recordings_df = create_dataframes.get_recordings_df(
            cls.mapped_listens_df, {}, RECOMMENDATION_RECORDINGS_DATAFRAME
        )

        cls.users_df = create_dataframes.get_users_dataframe(
            cls.mapped_listens_df, {}, RECOMMENDATION_RECORDING_USERS_DATAFRAME
        )

    @pytest.mark.skip
    def test_get_top_artist_candidate_set(self):
        top_artist_limit = 1
        top_artist_df = candidate_sets.get_top_artists(self.mapped_listens_subset, top_artist_limit, [])

        top_artist_candidate_set_df, top_artist_candidate_set_df_html = candidate_sets.get_top_artist_candidate_set(
            top_artist_df, self.recordings_df, self.users_df, self.mapped_listens_subset
        )
        self.assertCountEqual(['recording_id', 'spark_user_id', 'user_id'], top_artist_candidate_set_df.columns)
        self.assertEqual(top_artist_candidate_set_df.count(), 2)

        self.assertCountEqual(
            ['top_artist_credit_id', 'artist_credit_id', 'recording_mbid', 'recording_id', 'user_id', 'spark_user_id'],
            top_artist_candidate_set_df_html.columns
        )
        self.assertEqual(top_artist_candidate_set_df_html.count(), 2)

    @pytest.mark.skip
    def test_get_similar_artist_candidate_set_df(self):
        similar_artist_df = listenbrainz_spark.session.createDataFrame([
            Row(similar_artist_credit_id=2, similar_artist_name='martinkemp', user_id=1),
            Row(similar_artist_credit_id=2, similar_artist_name='martinkemp', user_id=4),
        ])

        similar_artist_candidate_set_df, similar_artist_candidate_set_df_html = candidate_sets.get_similar_artist_candidate_set(
            similar_artist_df, self.recordings_df, self.users_df, self.mapped_listens_subset
        )

        self.assertCountEqual(['recording_id', 'spark_user_id', 'user_id'], similar_artist_candidate_set_df.columns)
        self.assertEqual(similar_artist_candidate_set_df.count(), 2)

        self.assertCountEqual(
            ['similar_artist_credit_id', 'artist_credit_id', 'recording_mbid', 'recording_id', 'user_id', 'spark_user_id'],
            similar_artist_candidate_set_df_html.columns
        )
        self.assertEqual(similar_artist_candidate_set_df_html.count(), 2)

    def test_filter_last_x_days_recordings(self):
        top_artist_limit = 1
        top_artist_df = candidate_sets.get_top_artists(self.mapped_listens_df, top_artist_limit, [])

        _, candidate_set_df = candidate_sets.get_top_artist_candidate_set(
            top_artist_df, self.recordings_df, self.users_df, self.mapped_listens_subset
        )

        df = candidate_sets.filter_last_x_days_recordings(candidate_set_df, self.mapped_listens_subset)

        users = [row.user_id for row in df.collect()]
        self.assertEqual(sorted(users), [1, 4])
        received_recording_mbid = sorted([row.recording_mbid for row in df.collect()])
        expected_recording_mbid = sorted(
            ["sf5a56f4-1f83-4681-b319-70a734d0d047", "sf5a56f4-1f83-4681-b319-70a734d0d047"]
        )
        self.assertEqual(expected_recording_mbid, received_recording_mbid)
