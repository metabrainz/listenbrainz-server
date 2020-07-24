from datetime import datetime

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations import candidate_sets
from listenbrainz_spark import schema, utils, config, path, stats

from pyspark.sql import Row
import pyspark.sql.functions as f

class CandidateSetsTestClass(SparkTestCase):

    date = None
    recommendation_generation_window = 7

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
            listened_at=date,
            mb_artist_credit_id=credit_id,
            mb_artist_credit_mbids=["181c4177-f33a-441d-b15d-910acaf18b07"],
            mb_recording_mbid="3acb406f-c716-45f8-a8bd-96ca3939c2e5",
            mb_release_mbid="xxxxxx",
            msb_artist_credit_name_matchable="lessthanjake",
            msb_recording_name_matchable="Al's War",
            user_name=user_name,
        )
        return test_mapped_listens

    @classmethod
    def get_listens(cls):
        cls.date = datetime.utcnow()
        df1 = utils.create_dataframe(cls.get_listen_row(cls.date, 'vansika', 1), schema=None)
        shifted_date = stats.adjust_days(cls.date, cls.recommendation_generation_window + 1)
        df2 = utils.create_dataframe(cls.get_listen_row(shifted_date, 'vansika', 1), schema=None)
        shifted_date = stats.adjust_days(cls.date, 1)
        df3 = utils.create_dataframe(cls.get_listen_row(shifted_date, 'rob', 2), schema=None)
        shifted_date = stats.adjust_days(cls.date, 2)
        df4 = utils.create_dataframe(cls.get_listen_row(shifted_date, 'rob', 2), schema=None)
        test_mapped_df = df1.union(df2).union(df3).union(df4)
        return test_mapped_df

    def test_get_dates_to_generate_candidate_sets(self):
        mapped_df = self.get_listens()
        from_date, to_date = candidate_sets.get_dates_to_generate_candidate_sets(mapped_df,
                                                                                 self.recommendation_generation_window)
        self.assertEqual(to_date, self.date)
        expected_date = stats.adjust_days(self.date, self.recommendation_generation_window).replace(hour=0, minute=0, second=0)
        self.assertEqual(from_date, expected_date)

    def test_get_listens_to_fetch_top_artists(self):
        mapped_df = self.get_listens()
        from_date, to_date = candidate_sets.get_dates_to_generate_candidate_sets(mapped_df,
                                                                                 self.recommendation_generation_window)
        mapped_listens_subset = candidate_sets.get_listens_to_fetch_top_artists(mapped_df, from_date, to_date)
        self.assertEqual(mapped_listens_subset.count(), 3)

    def test_get_top_artists(self):
        mapped_listens = self.get_mapped_listens()
        top_artist_limit = 10
        test_top_artist = candidate_sets.get_top_artists(mapped_listens, top_artist_limit, [])

        cols = ['top_artist_credit_id', 'top_artist_name', 'user_name', 'total_count']
        self.assertListEqual(cols, test_top_artist.columns)
        self.assertEqual(test_top_artist.count(), 2)

        top_artist_id = sorted([row.top_artist_credit_id for row in test_top_artist.collect()])
        self.assertEqual(top_artist_id[0], 1)
        self.assertEqual(top_artist_id[1], 2)

    def test_get_similar_artists(self):
        df = utils.create_dataframe(
            Row(
                score=1.0,
                id_0=1,
                name_0="Less Than Jake",
                id_1=2,
                name_1="Wolfgang Amadeus Mozart"
            ),
            schema=None
        )

        df = df.union(utils.create_dataframe(
            Row(
                score=1.0,
                id_0=2,
                name_0="Wolfgang Amadeus Mozart",
                id_1=3,
                name_1="Katty Peri"
            ),
            schema=None
        ))

        artist_relation_df = df.union(utils.create_dataframe(
            Row(
                score=1.0,
                id_0=3,
                name_0="Katty Peri",
                id_1=1,
                name_1="Less Than Jake"
            ),
            schema=None
        ))

        top_artist_df = self.get_top_artist()

        similar_artist_limit = 10
        similar_artist_df, similar_artist_df_html = candidate_sets.get_similar_artists(top_artist_df, artist_relation_df,
                                                                                       similar_artist_limit)

        self.assertEqual(similar_artist_df.count(), 5)

        cols = [
            'similar_artist_credit_id', 'similar_artist_name', 'user_name'
        ]
        self.assertListEqual(cols, similar_artist_df.columns)

        self.assertEqual(similar_artist_df_html.count(), 6)
        cols = [
            'top_artist_credit_id',
            'top_artist_name',
            'similar_artist_credit_id',
            'similar_artist_name',
            'user_name'
        ]
        self.assertListEqual(cols, similar_artist_df_html.columns)

    def test_get_top_artist_candidate_set(self):
        recordings_df = self.get_recordings_df()
        users = self.get_users_df()

        df = utils.create_dataframe(
            Row(
                top_artist_credit_id=1,
                top_artist_name="lessthanjake",
                user_name='vansika'
            ),
            schema=None
        )

        top_artist_df = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name="kishorekumar",
                user_name='rob'
            ),
            schema=None
        ))

        top_artist_candidate_set_df, top_artist_candidate_set_df_html = candidate_sets.get_top_artist_candidate_set(top_artist_df,
                                                                                                                    recordings_df,
                                                                                                                    users)
        cols = ['recording_id', 'user_id', 'user_name']
        self.assertListEqual(sorted(cols), sorted(top_artist_candidate_set_df.columns))
        self.assertEqual(top_artist_candidate_set_df.count(), 2)

        cols = [
            'top_artist_credit_id',
            'top_artist_name',
            'mb_artist_credit_id',
            'mb_artist_credit_mbids',
            'mb_recording_mbid',
            'msb_artist_credit_name_matchable',
            'msb_recording_name_matchable',
            'recording_id',
            'user_name',
            'user_id'
        ]

        self.assertListEqual(sorted(cols), sorted(top_artist_candidate_set_df_html.columns))
        self.assertEqual(top_artist_candidate_set_df_html.count(), 2)

    def test_get_similar_artist_candidate_set_df(self):
        df = utils.create_dataframe(
            Row(
                similar_artist_credit_id=2,
                similar_artist_name='kishorekumar',
                user_name='rob'
            ),
            schema=None
        )

        similar_artist_df = df.union(utils.create_dataframe(
            Row(
                similar_artist_credit_id=3,
                similar_artist_name="kattyperi",
                user_name='vansika'
            ),
            schema=None
        ))

        recordings_df = self.get_recordings_df()
        users = self.get_users_df()

        similar_artist_candidate_set_df, similar_artist_candidate_set_df_html = candidate_sets.get_similar_artist_candidate_set(
                                                                                        similar_artist_df, recordings_df, users
                                                                                    )

        cols = ['recording_id', 'user_id', 'user_name']
        self.assertListEqual(sorted(cols), sorted(similar_artist_candidate_set_df.columns))
        self.assertEqual(similar_artist_candidate_set_df.count(), 1)

        cols = [
            'similar_artist_credit_id',
            'similar_artist_name',
            'mb_artist_credit_id',
            'mb_artist_credit_mbids',
            'mb_recording_mbid',
            'msb_artist_credit_name_matchable',
            'msb_recording_name_matchable',
            'recording_id',
            'user_name',
            'user_id'
        ]

        self.assertListEqual(sorted(cols), sorted(similar_artist_candidate_set_df_html.columns))
        self.assertEqual(similar_artist_candidate_set_df_html.count(), 1)

    def test_save_candidate_sets(self):
        top_artist_candidate_set_df_df = self.get_candidate_set()
        similar_artist_candidate_set_dfs_df = self.get_candidate_set()

        candidate_sets.save_candidate_sets(top_artist_candidate_set_df_df, similar_artist_candidate_set_dfs_df)
        top_artist_exist = utils.path_exists(path.TOP_ARTIST_CANDIDATE_SET)
        self.assertTrue(top_artist_exist)

        similar_artist_exist = utils.path_exists(path.SIMILAR_ARTIST_CANDIDATE_SET)
        self.assertTrue(top_artist_exist)

    def get_top_artist(self):
        df = utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name="blahblah",
                total_count=10,
                user_name='vansika_1'
            ),
            schema=None
        )

        df = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name="Less Than Jake",
                total_count=2,
                user_name='vansika'
            ),
            schema=None
        ))

        top_artist_df = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=1,
                top_artist_name="Less Than Jake",
                total_count=4,
                user_name='vansika'
            ),
            schema=None
        ))

        return top_artist_df

    def get_similar_artist_df_html(self):
        df = utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name="blahblah",
                similar_artist_credit_id=10,
                similar_artist_name='Monali',
                user_name='vansika_1'
            ),
            schema=None
        )

        df = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name="Less Than Jake",
                similar_artist_credit_id=1,
                similar_artist_name='shan',
                user_name='vansika'
            ),
            schema=None
        ))

        similar_artist_df_html = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=1,
                top_artist_name="Less Than Jake",
                similar_artist_credit_id=90,
                similar_artist_name='john',
                user_name='vansika'
            ),
            schema=None
        ))

        return similar_artist_df_html

    def get_top_artist_candidate_set_df_html(self):
        df = utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name="blahblah",
                mb_artist_credit_id=1,
                mb_artist_credit_mbids=['xxx'],
                mb_recording_mbid='yyy',
                msb_artist_credit_name_matchable='blahblah',
                msb_recording_name_matchable='looloo',
                recording_id=2,
                user_name='vansika_1'
            ),
            schema=None
        )

        df = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name="Less Than Jake",
                mb_artist_credit_id=1,
                mb_artist_credit_mbids=['xxx'],
                mb_recording_mbid='yyy',
                msb_artist_credit_name_matchable='lessthanjake',
                msb_recording_name_matchable='lalal',
                recording_id=2,
                user_name='vansika'
            ),
            schema=None
        ))

        top_artist_candidate_set_df_html = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=1,
                top_artist_name="Less Than Jake",
                mb_artist_credit_id=1,
                mb_artist_credit_mbids=['xxx'],
                mb_recording_mbid='yyy',
                msb_artist_credit_name_matchable='lessthanjake',
                msb_recording_name_matchable='lalal',
                recording_id=2,
                user_name='vansika',
            ),
            schema=None
        ))

        return top_artist_candidate_set_df_html

    def get_similar_artist_candidate_set_df_html(self):
        df = utils.create_dataframe(
            Row(
                similar_artist_credit_id=2,
                similar_artist_name="blahblah",
                mb_artist_credit_id=1,
                mb_artist_credit_mbids=['xxx'],
                mb_recording_mbid='yyy',
                msb_artist_credit_name_matchable='blahblah',
                msb_recording_name_matchable='looloo',
                recording_id=2,
                user_name='vansika_1'
            ),
            schema=None
        )

        similar_artist_candidate_set_df_html = df.union(utils.create_dataframe(
            Row(
                similar_artist_credit_id=1,
                similar_artist_name="Less Than Jake",
                mb_artist_credit_id=1,
                mb_artist_credit_mbids=['xxx'],
                mb_recording_mbid='yyy',
                msb_artist_credit_name_matchable='lessthanjake',
                msb_recording_name_matchable='lalal',
                recording_id=2,
                user_name='vansika',
            ),
            schema=None
        ))

        return similar_artist_candidate_set_df_html

    def test_get_candidate_html_data(self):
        top_artist_df = self.get_top_artist()
        similar_artist_df_html = self.get_similar_artist_df_html()
        top_artist_candidate_set_df_html = self.get_top_artist_candidate_set_df_html()
        similar_artist_candidate_set_df_html = self.get_similar_artist_candidate_set_df_html()

        received_user_data = candidate_sets.get_candidate_html_data(similar_artist_candidate_set_df_html,
                                                                    top_artist_candidate_set_df_html,
                                                                    top_artist_df, similar_artist_df_html)

        expected_user_data = {
            'vansika': {
                'top_artist': [
                    ("Less Than Jake", 2, 2), ("Less Than Jake", 1, 4)
                ],
                'similar_artist': [
                    ("Less Than Jake", 2, 'shan', 1), ("Less Than Jake", 1, 'john', 90)
                ],
                'top_artist_candidate_set': [
                    (2, "Less Than Jake", 1, ['xxx'], 'yyy', 'lessthanjake', 'lalal', 2),
                    (1, "Less Than Jake", 1, ['xxx'], 'yyy', 'lessthanjake', 'lalal', 2)
                ],
                'similar_artist_candidate_set': [
                    (1, "Less Than Jake", 1, ['xxx'], 'yyy', 'lessthanjake', 'lalal', 2)
                ]
            },

            'vansika_1': {
                'top_artist': [
                    ("blahblah", 2, 10)
                ],
                'similar_artist': [
                    ("blahblah", 2, 'Monali', 10)
                ],
                'top_artist_candidate_set': [
                    (2, "blahblah", 1, ['xxx'], 'yyy', 'blahblah', 'looloo', 2)
                ],
                'similar_artist_candidate_set': [
                    (2, "blahblah", 1, ['xxx'], 'yyy', 'blahblah', 'looloo', 2)
                ]
            }
        }

        self.assertEqual(received_user_data['vansika']['top_artist'], expected_user_data['vansika']['top_artist'])
        self.assertEqual(received_user_data['vansika']['similar_artist'], expected_user_data['vansika']['similar_artist'])
        self.assertEqual(received_user_data['vansika']['top_artist_candidate_set'],
                         expected_user_data['vansika']['top_artist_candidate_set'])
        self.assertEqual(received_user_data['vansika']['similar_artist_candidate_set'],
                         expected_user_data['vansika']['similar_artist_candidate_set'])

        self.assertEqual(received_user_data['vansika_1']['top_artist'], expected_user_data['vansika_1']['top_artist'])
        self.assertEqual(received_user_data['vansika_1']['similar_artist'], expected_user_data['vansika_1']['similar_artist'])
        self.assertEqual(received_user_data['vansika_1']['top_artist_candidate_set'],
                         expected_user_data['vansika_1']['top_artist_candidate_set'])
        self.assertEqual(received_user_data['vansika_1']['similar_artist_candidate_set'],
                         expected_user_data['vansika_1']['similar_artist_candidate_set'])
