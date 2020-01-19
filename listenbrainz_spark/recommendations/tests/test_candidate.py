from datetime import datetime

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import candidate_sets
from listenbrainz_spark import schema, utils, config, path, stats

from pyspark.sql import Row
import pyspark.sql.functions as f

class CandidateSetsTestClass(SparkTestCase):

    date = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    @classmethod
    def get_listen_row(cls, date, user_name, credit_id):
        test_mapped_listens = Row(
            user_name=user_name, artist_msid="a36d6fc9-49d0-4789-a7dd-a2b72369ca45", release_msid="xxxxxx",
            release_name="xxxxxx", artist_name="Less Than Jake", release_mbid="xxxxxx", track_name="Al's War",
            recording_msid="cb6985cd-cc71-4d59-b4fb-2e72796af741", tags=['xxxx'], listened_at=date,
            msb_recording_msid="cb6985cd-cc71-4d59-b4fb-2e72796af741", mb_recording_gid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
            msb_artist_msid="a36d6fc9-49d0-4789-a7dd-a2b72369ca45", mb_artist_gids=["181c4177-f33a-441d-b15d-910acaf18b07"],
            mb_artist_credit_id=credit_id
        )
        return test_mapped_listens

    @classmethod
    def get_listens(cls):
        cls.date = datetime.utcnow()
        df1 = utils.create_dataframe([cls.get_listen_row(cls.date, 'vansika', 1)], schema=None)
        shifted_date = stats.adjust_days(cls.date, config.RECOMMENDATION_GENERATION_WINDOW + 1)
        df2 = utils.create_dataframe([cls.get_listen_row(shifted_date, 'vansika', 1)], schema=None)
        shifted_date = stats.adjust_days(cls.date, 1, shift_backwards=False)
        df3 = utils.create_dataframe([cls.get_listen_row(shifted_date, 'rob', 2)], schema=None)
        shifted_date = stats.adjust_days(cls.date, 2)
        df4 = utils.create_dataframe([cls.get_listen_row(shifted_date, 'rob', 2)], schema=None)
        test_mapped_df = df1.union(df2).union(df3).union(df4)
        return test_mapped_df

    def test_get_listens_for_rec_generation_window(self):
        mapped_df = self.get_listens()
        test_df = candidate_sets.get_listens_for_rec_generation_window(mapped_df)
        min_date = test_df.select(f.min('listened_at').alias('listened_at')).take(1)[0]
        max_date = test_df.select(f.max('listened_at').alias('listened_at')).take(1)[0]
        self.assertGreaterEqual(self.date, min_date.listened_at)
        self.assertLessEqual(self.date, max_date.listened_at)

    def test_get_top_artists(self):
        mapped_df = self.get_mapped_listens()
        test_top_artist_df = candidate_sets.get_top_artists(mapped_df, 'vansika')
        self.assertListEqual(['mb_artist_credit_id', 'artist_name', 'count'], test_top_artist_df.columns)
        self.assertEqual(test_top_artist_df.count(), 1)
        row = test_top_artist_df.collect()[0]
        self.assertEqual(row.mb_artist_credit_id, 1)

    def test_get_similar_artists(self):
        df = utils.create_dataframe([Row(score=1.0, id_0=1, name_0="Less Than Jake", id_1=2,
            name_1="Wolfgang Amadeus Mozart")], schema=None)
        artist_relation_df = df.union(utils.create_dataframe([Row(score=1.0, id_0=3, name_0="Katty Peri", id_1=1,
            name_1="Less Than Jake")], schema=None))

        top_artist_df = utils.create_dataframe([Row(mb_artist_credit_id=1, artist_name="Less Than Jake", count=1)],
            schema=None)
        similar_artist_df = candidate_sets.get_similar_artists(top_artist_df, artist_relation_df, 'vansika')
        self.assertEqual(similar_artist_df.count(), 2)
        cols = ['top_artist_credit_id', 'similar_artist_credit_id', 'similar_artist_name', 'top_artist_name']
        self.assertListEqual(cols, similar_artist_df.columns)

        artist_relation_df = utils.create_dataframe([Row(score=1.0, id_0=3, name_0="Katty Peri", id_1=2,
            name_1="Alka Yagnik")], schema=None)
        with self.assertRaises(IndexError):
            candidate_sets.get_similar_artists(top_artist_df, artist_relation_df, 'vansika')

        df = utils.create_dataframe([Row(mb_artist_credit_id=1, artist_name="Less Than Jake", count=1)], schema=None)
        top_artist_df = df.union(utils.create_dataframe([Row(mb_artist_credit_id=2, artist_name="Katty Peri", count=1)],
            schema=None))
        artist_relation_df = utils.create_dataframe([Row(score=1.0, id_0=2, name_0="Katty Peri", id_1=1,
            name_1="Less Than Jake")], schema=None)
        with self.assertRaises(IndexError):
            candidate_sets.get_similar_artists(top_artist_df, artist_relation_df, 'vansika')

    def test_get_candidate_recording_ids(self):
        recordings_df = self.get_recordings_df()
        recording_ids = candidate_sets.get_candidate_recording_ids([1, 2], recordings_df, 1)
        self.assertListEqual(['user_id', 'recording_id'], recording_ids.columns)
        self.assertEqual(recording_ids.count(), 2)

    def test_get_top_artists_recording_ids(self):
        recordings_df = self.get_recordings_df()
        df = utils.create_dataframe([Row(mb_artist_credit_id=1, artist_name="Less Than Jake", count=1)], schema=None)
        top_artist_df = df.union(utils.create_dataframe([Row(mb_artist_credit_id=2, artist_name="Kishore Kumar", count=1)],
            schema=None))
        recording_ids = candidate_sets.get_top_artists_recording_ids(top_artist_df, recordings_df, 1)
        self.assertListEqual(['user_id', 'recording_id'], recording_ids.columns)
        self.assertEqual(recording_ids.count(), 2)

    def test_get_similar_artist_recording_ids(self):
        df = utils.create_dataframe([Row(top_artist_credit_id=1, similar_artist_credit_id=2,
            similar_artist_name='Kishore Kumar', top_artist_name="Less Than Jake")], schema=None)
        similar_artist_df = df.union(utils.create_dataframe([Row(top_artist_credit_id=2, similar_artist_credit_id=1,
            similar_artist_name="Kishore Kumar", top_artist_name="Less Than Jake")], schema=None))

        recordings_df = self.get_recordings_df()
        recording_ids = candidate_sets.get_similar_artists_recording_ids(similar_artist_df, recordings_df, 1)
        self.assertListEqual(['user_id', 'recording_id'], recording_ids.columns)
        self.assertEqual(recording_ids.count(), 2)

    def test_get_user_id(self):
        users_df = self.get_users_df()
        user_id = candidate_sets.get_user_id(users_df, 'vansika')
        self.assertEqual(user_id, 1)

        with self.assertRaises(IndexError):
            candidate_sets.get_user_id(users_df, 'invalid name')

    def test_save_candidate_sets(self):
        top_artist_candidate_sets_df = self.get_candidate_set()
        similar_artist_candidate_sets_df = self.get_candidate_set()

        candidate_sets.save_candidate_sets(top_artist_candidate_sets_df, similar_artist_candidate_sets_df)
        top_artist_exist = utils.path_exists(path.TOP_ARTIST_CANDIDATE_SET)
        self.assertTrue(top_artist_exist)

        similar_artist_exist = utils.path_exists(path.SIMILAR_ARTIST_CANDIDATE_SET)
        self.assertTrue(top_artist_exist)
