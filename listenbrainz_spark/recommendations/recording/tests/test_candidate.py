import os
from datetime import datetime

import pyspark.sql.functions as f
from pyspark.sql import Row
from pyspark.sql.types import StructField, StructType, StringType

import listenbrainz_spark
from listenbrainz_spark import utils, path
from listenbrainz_spark.exceptions import TopArtistNotFetchedException
from listenbrainz_spark.hdfs.utils import path_exists
from listenbrainz_spark.path import RECOMMENDATION_RECORDING_MAPPED_LISTENS
from listenbrainz_spark.recommendations.recording import candidate_sets
from listenbrainz_spark.recommendations.recording.tests import RecommendationsTestCase
from listenbrainz_spark.tests import TEST_DATA_PATH


class CandidateSetsTestClass(RecommendationsTestCase):

    @classmethod
    def setUpClass(cls):
        super(CandidateSetsTestClass, cls).setUpClass()
        cls.mapped_listens_subset = listenbrainz_spark \
            .session \
            .read \
            .parquet("file://" + os.path.join(TEST_DATA_PATH, 'mapped_listens_subset.parquet'))

    def test_get_dates_to_generate_candidate_sets(self):
        mapped_df = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        from_date, to_date = candidate_sets.get_dates_to_generate_candidate_sets(mapped_df, 7)
        self.assertEqual(to_date, datetime(2021, 8, 9, 10, 20, 11))
        self.assertEqual(from_date, datetime(2021, 8, 2))

    def test_get_listens_to_fetch_top_artists(self):
        mapped_df = utils.read_files_from_HDFS(RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        from_date, to_date = candidate_sets.get_dates_to_generate_candidate_sets(mapped_df, 7)
        mapped_listens_subset = candidate_sets.get_listens_to_fetch_top_artists(mapped_df, from_date, to_date)
        self.assertCountEqual(list(mapped_listens_subset.toLocalIterator()), list(self.mapped_listens_subset.toLocalIterator()))
        self.assertEqual(mapped_listens_subset.count(), 11)

    def test_get_top_artists(self):
        top_artist_limit = 1
        test_top_artist = candidate_sets.get_top_artists(self.mapped_listens_subset, top_artist_limit, [])

        self.assertCountEqual(['top_artist_credit_id', 'user_id'], test_top_artist.columns)
        self.assertEqual(test_top_artist.count(), 2)

        # empty df
        mapped_listens = self.mapped_listens_subset.select('*').where(f.col('user_id') == 100)
        with self.assertRaises(TopArtistNotFetchedException):
            candidate_sets.get_top_artists(mapped_listens, top_artist_limit, [])

        with self.assertRaises(TopArtistNotFetchedException):
            candidate_sets.get_top_artists(mapped_listens, top_artist_limit, ['lala'])

    def test_save_candidate_sets(self):
        top_artist_candidate_set_df_df = self.get_candidate_set()
        candidate_sets.save_candidate_sets(top_artist_candidate_set_df_df)
        top_artist_exist = path_exists(path.RECOMMENDATION_RECORDING_TOP_ARTIST_CANDIDATE_SET)
        self.assertTrue(top_artist_exist)

    def get_top_artist(self):
        return listenbrainz_spark.session.createDataFrame([
            Row(top_artist_credit_id=2, user_id=4),
            Row(top_artist_credit_id=2, user_id=3),
            Row(top_artist_credit_id=1, user_id=3),
        ])

    def get_top_artist_candidate_set_df_html(self):
        return listenbrainz_spark.session.createDataFrame([
            Row(top_artist_credit_id=2, artist_credit_id=1, artist_credit_mbids=['xxx'],
                recording_mbid='yyy', recording_id=2, user_id=4),
            Row(top_artist_credit_id=2, artist_credit_id=1, artist_credit_mbids=['xxx'],
                recording_mbid='yyy', recording_id=2, user_id=3),
            Row(top_artist_credit_id=1, artist_credit_id=1, artist_credit_mbids=['xxx'],
                recording_mbid='yyy', recording_id=2, user_id=3,),
        ])

    def test_get_candidate_html_data(self):
        top_artist_df = self.get_top_artist()
        top_artist_candidate_set_df_html = self.get_top_artist_candidate_set_df_html()

        received_user_data = candidate_sets.get_candidate_html_data(top_artist_candidate_set_df_html, top_artist_df)

        expected_user_data = {
            3: {
                'top_artist': [2, 1],
                'top_artist_candidate_set': [(2, 1, 'yyy', 2), (1, 1, 'yyy', 2)],
            },
            4: {
                'top_artist': [2],
                'top_artist_candidate_set': [(2, 1, 'yyy', 2)],
            }
        }

        self.assertEqual(received_user_data[3]['top_artist'], expected_user_data[3]['top_artist'])
        self.assertEqual(received_user_data[3]['top_artist_candidate_set'],
                         expected_user_data[3]['top_artist_candidate_set'])

        self.assertEqual(received_user_data[4]['top_artist'], expected_user_data[4]['top_artist'])
        self.assertEqual(received_user_data[4]['top_artist_candidate_set'],
                         expected_user_data[4]['top_artist_candidate_set'])

    def test_is_empty_dataframe(self):
        df = utils.create_dataframe(Row(col1='la'), schema=StructType([StructField('col1', StringType())]))

        status = candidate_sets._is_empty_dataframe(df)
        self.assertFalse(status)

        # empty df
        df = df.select('*').where(f.col('col1') == 'laa')
        status = candidate_sets._is_empty_dataframe(df)
        self.assertTrue(status)
