from datetime import datetime
import sys
from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.recommendations.recording import candidate_sets
from listenbrainz_spark.recommendations.recording import create_dataframes
from listenbrainz_spark import schema, utils, config, path, stats
from listenbrainz_spark.exceptions import (TopArtistNotFetchedException,
                                           SimilarArtistNotFetchedException)

from pyspark.sql import Row
from unittest.mock import patch
import pyspark.sql.functions as f
from pyspark.sql.types import StructField, StructType, StringType

class CandidateSetsTestClass(SparkTestCase):

    recommendation_generation_window = 7
    listens_path = path.LISTENBRAINZ_DATA_DIRECTORY
    mapping_path = path.MBID_MSID_MAPPING
    mapped_listens_path = path.RECOMMENDATION_RECORDING_MAPPED_LISTENS
    mapped_listens_subset_path = '/mapped/subset.parquet'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upload_test_listen_to_hdfs(cls.listens_path)
        cls.upload_test_mapping_to_hdfs(cls.mapping_path)
        cls.upload_test_mapped_listens_to_hdfs(cls.listens_path, cls.mapping_path, cls.mapped_listens_path)
        cls.upload_test_mapping_listens_subset_to_hdfs()

    @classmethod
    def tearDownClass(cls):
        super().delete_dir()
        super().tearDownClass()

    @classmethod
    def upload_test_mapping_listens_subset_to_hdfs(cls):
        mapped_df = utils.read_files_from_HDFS(cls.mapped_listens_path)
        from_date = stats.offset_days(cls.date, 4)
        to_date = cls.date
        mapped_listens_subset = candidate_sets.get_listens_to_fetch_top_artists(mapped_df, from_date, to_date)
        utils.save_parquet(mapped_listens_subset, cls.mapped_listens_subset_path)

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
        shifted_date = stats.offset_days(cls.date, cls.recommendation_generation_window + 1)
        df2 = utils.create_dataframe(cls.get_listen_row(shifted_date, 'vansika', 1), schema=None)
        shifted_date = stats.offset_days(cls.date, 1)
        df3 = utils.create_dataframe(cls.get_listen_row(shifted_date, 'rob', 2), schema=None)
        shifted_date = stats.offset_days(cls.date, 2)
        df4 = utils.create_dataframe(cls.get_listen_row(shifted_date, 'rob', 2), schema=None)
        test_mapped_df = df1.union(df2).union(df3).union(df4)
        return test_mapped_df

    def test_get_dates_to_generate_candidate_sets(self):
        mapped_df = self.get_listens()
        from_date, to_date = candidate_sets.get_dates_to_generate_candidate_sets(mapped_df,
                                                                                 self.recommendation_generation_window)
        self.assertEqual(to_date, self.date)
        expected_date = stats.offset_days(self.date, self.recommendation_generation_window).replace(hour=0, minute=0, second=0)
        self.assertEqual(from_date, expected_date)

    def test_get_listens_to_fetch_top_artists(self):
        mapped_df = self.get_listens()
        from_date, to_date = candidate_sets.get_dates_to_generate_candidate_sets(mapped_df,
                                                                                 self.recommendation_generation_window)
        mapped_listens_subset = candidate_sets.get_listens_to_fetch_top_artists(mapped_df, from_date, to_date)
        self.assertEqual(mapped_listens_subset.count(), 3)

    def test_get_top_artists(self):
        mapped_listens = utils.read_files_from_HDFS(self.mapped_listens_path)
        top_artist_limit = 1
        test_top_artist = candidate_sets.get_top_artists(mapped_listens, top_artist_limit, [])

        cols = ['top_artist_credit_id', 'top_artist_name', 'user_name', 'total_count']
        self.assertListEqual(sorted(cols), sorted(test_top_artist.columns))
        self.assertEqual(test_top_artist.count(), 4)

        # empty df
        mapped_listens = mapped_listens.select('*').where(f.col('user_name') == 'lala')
        with self.assertRaises(TopArtistNotFetchedException):
            candidate_sets.get_top_artists(mapped_listens, top_artist_limit, [])

        with self.assertRaises(TopArtistNotFetchedException):
            candidate_sets.get_top_artists(mapped_listens, top_artist_limit, ['lala'])

    def test_get_similar_artists(self):
        df = utils.create_dataframe(
            Row(
                score=1.0,
                id_0=1,
                name_0="Less Than Jake",
                id_1=2,
                name_1="blahblah"
            ),
            schema=None
        )

        df = df.union(utils.create_dataframe(
            Row(
                score=1.0,
                id_0=2,
                name_0="blahblah",
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

        self.assertEqual(similar_artist_df.count(), 3)

        cols = [
            'similar_artist_credit_id', 'similar_artist_name', 'user_name'
        ]
        self.assertListEqual(cols, similar_artist_df.columns)

        self.assertEqual(similar_artist_df_html.count(), 4)
        cols = [
            'top_artist_credit_id',
            'top_artist_name',
            'similar_artist_credit_id',
            'similar_artist_name',
            'user_name'
        ]
        self.assertListEqual(cols, similar_artist_df_html.columns)

        artist_relation_df = utils.create_dataframe(
            Row(
                score=1.0,
                id_0=6,
                name_0="Less Than Jake",
                id_1=7,
                name_1="Wolfgang Amadeus Mozart"
            ),
            schema=None
        )
        with self.assertRaises(SimilarArtistNotFetchedException):
            candidate_sets.get_similar_artists(top_artist_df, artist_relation_df, similar_artist_limit)

    def test_get_top_artist_candidate_set(self):
        mapped_listens_df = utils.read_files_from_HDFS(self.mapped_listens_path)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens_df, {})
        users = create_dataframes.get_users_dataframe(mapped_listens_df, {})
        mapped_listens_subset = utils.read_files_from_HDFS(self.mapped_listens_subset_path)

        top_artist_limit = 1
        top_artist_df = candidate_sets.get_top_artists(mapped_listens_subset, top_artist_limit, [])

        top_artist_candidate_set_df, top_artist_candidate_set_df_html = candidate_sets.get_top_artist_candidate_set(top_artist_df,
                                                                                                                    recordings_df,
                                                                                                                    users,
                                                                                                                    mapped_listens_subset)
        cols = ['recording_id', 'user_id', 'user_name']
        self.assertListEqual(sorted(cols), sorted(top_artist_candidate_set_df.columns))
        self.assertEqual(top_artist_candidate_set_df.count(), 3)

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
        self.assertEqual(top_artist_candidate_set_df_html.count(), 3)

    def test_get_similar_artist_candidate_set_df(self):
        mapped_listens_df = utils.read_files_from_HDFS(self.mapped_listens_path)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens_df, {})
        users = create_dataframes.get_users_dataframe(mapped_listens_df, {})
        mapped_listens_subset = utils.read_files_from_HDFS(self.mapped_listens_subset_path)

        df = utils.create_dataframe(
            Row(
                similar_artist_credit_id=2,
                similar_artist_name='martinkemp',
                user_name='rob'
            ),
            schema=None
        )

        similar_artist_df = df.union(utils.create_dataframe(
            Row(
                similar_artist_credit_id=2,
                similar_artist_name='martinkemp',
                user_name='vansika_1'
            ),
            schema=None
        ))

        similar_artist_candidate_set_df, similar_artist_candidate_set_df_html = candidate_sets.get_similar_artist_candidate_set(
                                                                                        similar_artist_df, recordings_df, users,
                                                                                        mapped_listens_subset
                                                                                    )

        cols = ['recording_id', 'user_id', 'user_name']
        self.assertListEqual(sorted(cols), sorted(similar_artist_candidate_set_df.columns))
        self.assertEqual(similar_artist_candidate_set_df.count(), 2)

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
        self.assertEqual(similar_artist_candidate_set_df_html.count(), 2)

    def test_filter_last_x_days_recordings(self):
        mapped_listens_df = utils.read_files_from_HDFS(self.mapped_listens_path)
        mapped_listens_subset = utils.read_files_from_HDFS(self.mapped_listens_subset_path)
        recordings_df = create_dataframes.get_recordings_df(mapped_listens_df, {})
        users = create_dataframes.get_users_dataframe(mapped_listens_df, {})
        mapped_listens_subset = utils.read_files_from_HDFS(self.mapped_listens_subset_path)

        top_artist_limit = 1
        top_artist_df = candidate_sets.get_top_artists(mapped_listens_subset, top_artist_limit, [])

        _, candidate_set_df = candidate_sets.get_top_artist_candidate_set(top_artist_df,
                                                                          recordings_df,
                                                                          users,
                                                                          mapped_listens_subset)

        df = candidate_sets.filter_last_x_days_recordings(candidate_set_df, mapped_listens_subset)

        user_name = [row.user_name for row in df.collect()]
        self.assertEqual(sorted(user_name), ['rob', 'rob', 'vansika_1'])
        received_recording_mbid = sorted([row.mb_recording_mbid for row in df.collect()])
        expected_recording_mbid = sorted(
            ["sf5a56f4-1f83-4681-b319-70a734d0d047", "af5a56f4-1f83-4681-b319-70a734d0d047", "sf5a56f4-1f83-4681-b319-70a734d0d047"]
        )
        self.assertEqual(expected_recording_mbid, received_recording_mbid)

    def test_save_candidate_sets(self):
        top_artist_candidate_set_df_df = self.get_candidate_set()
        similar_artist_candidate_set_dfs_df = self.get_candidate_set()

        candidate_sets.save_candidate_sets(top_artist_candidate_set_df_df, similar_artist_candidate_set_dfs_df)
        top_artist_exist = utils.path_exists(path.RECOMMENDATION_RECORDING_TOP_ARTIST_CANDIDATE_SET)
        self.assertTrue(top_artist_exist)

        similar_artist_exist = utils.path_exists(path.RECOMMENDATION_RECORDING_SIMILAR_ARTIST_CANDIDATE_SET)
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
                top_artist_name="blahblah",
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
                top_artist_name="blahblah",
                similar_artist_credit_id=1,
                similar_artist_name='Less Than Jake',
                user_name='vansika_1'
            ),
            schema=None
        ))

        df = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name="blahblah",
                similar_artist_credit_id=1,
                similar_artist_name="Less Than Jake",
                user_name='vansika'
            ),
            schema=None
        ))

        df = df.union(utils.create_dataframe(
            Row(
                top_artist_credit_id=1,
                top_artist_name="Less Than Jake",
                similar_artist_credit_id=2,
                similar_artist_name="blahblah",
                user_name='vansika',
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
                    ('blahblah', 2, 2), ('Less Than Jake', 1, 4)
                ],
                'similar_artist': [
                    ('blahblah', 2, 'Less Than Jake', 1), ('Less Than Jake', 1, 'blahblah', 2),
                    ('Less Than Jake', 1, 'john', 90)
                ],
                'top_artist_candidate_set': [
                    (2, 'Less Than Jake', 1, ['xxx'], 'yyy', 'lessthanjake', 'lalal', 2),
                    (1, 'Less Than Jake', 1, ['xxx'], 'yyy', 'lessthanjake', 'lalal', 2)
                ],
                'similar_artist_candidate_set': [
                    (1, 'Less Than Jake', 1, ['xxx'], 'yyy', 'lessthanjake', 'lalal', 2)
                ]
            },

            'vansika_1': {
                'top_artist': [
                    ('blahblah', 2, 10)
                ],
                'similar_artist': [
                    ('blahblah', 2, 'Monali', 10), ('blahblah', 2, 'Less Than Jake', 1)
                ],
                'top_artist_candidate_set': [
                    (2, 'blahblah', 1, ['xxx'], 'yyy', 'blahblah', 'looloo', 2)
                ],
                'similar_artist_candidate_set': [
                    (2, 'blahblah', 1, ['xxx'], 'yyy', 'blahblah', 'looloo', 2)
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

    def test_filter_top_artists_from_similar_artists(self):
        similar_artist_df = self.get_similar_artist_df_html()
        top_artist_df = self.get_top_artist()

        df = candidate_sets.filter_top_artists_from_similar_artists(similar_artist_df, top_artist_df)
        self.assertEqual(df.count(), 3)

    def test_is_empty_dataframe(self):
        df = utils.create_dataframe(Row(col1='la'), schema=StructType([StructField('col1', StringType())]))

        status = candidate_sets._is_empty_dataframe(df)
        self.assertFalse(status)

        # empty df
        df = df.select('*').where(f.col('col1') == 'laa')
        status = candidate_sets._is_empty_dataframe(df)
        self.assertTrue(status)

    def test_convert_string_datatype_to_array(self):
        df = utils.create_dataframe(Row(mbids="6a70b322-9aa9-41b3-9dce-824733633a1c"), schema=None)

        res_df = candidate_sets.convert_string_datatype_to_array(df)
        self.assertEqual(res_df.collect()[0].mb_artist_credit_mbids, ["6a70b322-9aa9-41b3-9dce-824733633a1c"])

    def test_explode_artist_collaborations(self):
        df = utils.create_dataframe(
            Row(
                mb_artist_credit_mbids=["5a70b322-9aa9-41b3-9dce-824733633a1c"],
                user_name="vansika",
                total_count=1
            ),
            schema=None
        )

        df = df.union(utils.create_dataframe(
            Row(
                mb_artist_credit_mbids=["6a70b322-9aa9-41b3-9dce-824733633a1c", "7a70b322-9aa9-41b3-9dce-824733633a1c"],
                user_name="vansika",
                total_count=4
            ),
            schema=None
        ))

        res_df = candidate_sets.explode_artist_collaborations(df)
        self.assertEqual(sorted(res_df.columns), sorted(["mb_artist_credit_mbids", "user_name", "total_count"]))
        self.assertEqual(res_df.collect()[0].mb_artist_credit_mbids, ["6a70b322-9aa9-41b3-9dce-824733633a1c"])
        self.assertEqual(res_df.collect()[1].mb_artist_credit_mbids, ["7a70b322-9aa9-41b3-9dce-824733633a1c"])

    @patch('listenbrainz_spark.recommendations.recording.candidate_sets.utils.read_files_from_HDFS')
    @patch('listenbrainz_spark.recommendations.recording.candidate_sets.explode_artist_collaborations')
    def test_append_artists_from_collaborations(self, mock_explode, mock_read_hdfs):
        top_artist_df = utils.create_dataframe(
            Row(
                top_artist_credit_id=2,
                top_artist_name='kishorekumar',
                user_name='vansika',
                mb_artist_credit_mbids=["6a70b322-9aa9-41b3-9dce-824733633a1c"],
                total_count=4),
            schema=None
        )
        mock_explode.return_value = utils.create_dataframe(
            Row(
                mb_artist_credit_mbids=["6a70b322-9aa9-41b3-9dce-824733633a1c"],
                user_name='rob',
                total_count=7
            ),
            schema=None
        )

        mapping_df = utils.create_dataframe(
            Row(
                mb_artist_credit_mbids=["6a70b322-9aa9-41b3-9dce-824733633a1c"],
                msb_artist_credit_name_matchable='kishorekumar',
                mb_artist_credit_id=2,
            ),
            schema=None
        )

        mock_read_hdfs.return_value = mapping_df
        res_df = candidate_sets.append_artists_from_collaborations(top_artist_df)

        mock_explode.assert_called_once_with(top_artist_df)
        mock_read_hdfs.assert_called_once_with(path.MBID_MSID_MAPPING)

        self.assertEqual(res_df.count(), 2)
        self.assertEqual(res_df.collect()[0].user_name, 'vansika')
        self.assertEqual(res_df.collect()[1].user_name, 'rob')
