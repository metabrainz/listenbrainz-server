from pyspark.sql import Row

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.stats.user.all import calculate
from listenbrainz_spark import utils

class UserStatsAllTestCase(SparkTestCase):

    def save_dataframe(self):
        df = utils.create_dataframe(Row(user_name='user2', artist_name='artist1', artist_msid='1',artist_mbids='1',
            track_name='test', recording_msid='1', recording_mbid='1', release_name='test',release_msid='1',
            release_mbid='1'), schema=None)
        df1 = utils.create_dataframe(Row(user_name='user1',artist_name='artist1', artist_msid='1',artist_mbids='1',
            track_name='test', recording_msid='1', recording_mbid='1', release_name='test',release_msid='1',
             release_mbid='1'), schema=None)
        df2 = utils.create_dataframe(Row(user_name='user1',artist_name='artist1', artist_msid='1',artist_mbids='1',
            track_name='test', recording_msid='1', recording_mbid='1', release_name='test',release_msid='1',
            release_mbid='1'), schema=None)
        df = df.union(df1).union(df2)
        utils.save_parquet(df, '/data/listenbrainz/2019/12.parquet')

    def test_all(self):
        self.save_dataframe()
        data = calculate()
        expected_result = [
            {
                "musicbrainz_id": "user1",
                "type": "user_artist",
                "artist_stats": [
                    {
                        "artist_name": "artist1",
                        "artist_msid": "1",
                        "artist_mbids": "1",
                        "listen_count": 2
                    }
                ],
                "artist_count": 1
            },
            {
                "musicbrainz_id": "user2",
                "type": "user_artist",
                "artist_stats": [
                    {
                        "artist_name": "artist1",
                        "artist_msid": "1",
                        "artist_mbids": "1",
                        "listen_count": 1
                    }
                ],
                "artist_count": 1
            }
        ]
        self.assertListEqual(expected_result, data)
        self.assertDictEqual(expected_result[0], data[0])
        self.assertDictEqual(expected_result[1], data[1])
