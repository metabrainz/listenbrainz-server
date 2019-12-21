from listenbrainz_spark.stats import user
from listenbrainz_spark import utils
from listenbrainz_spark.tests import SparkTestCase

from pyspark.sql import Row

class UtilsTestCase(SparkTestCase):
    
    def create_df(self):
        df = utils.create_dataframe(Row(user_name='user2', artist_name='artist1', artist_msid='1',artist_mbids='1',track_name='test', recording_msid='1', recording_mbid='1', release_name='test',release_msid='1', release_mbid='1'), schema=None)
        df1 = utils.create_dataframe(Row(user_name='user1',artist_name='artist1', artist_msid='1',artist_mbids='1',track_name='test', recording_msid='1', recording_mbid='1', release_name='test',release_msid='1', release_mbid='1'), schema=None)
        df = df.union(df1)
        df2 = utils.create_dataframe(Row(user_name='user1',artist_name='artist1', artist_msid='1',artist_mbids='1',track_name='test', recording_msid='1', recording_mbid='1', release_name='test',release_msid='1', release_mbid='1'), schema=None)
        df = df.union(df2)
        return df
    
    def test_get_artists(self):
        df = self.create_df()
        df.createOrReplaceTempView('table')
        dictionary = {
                    'user1': [{
                        'artist_name': 'artist1',
                        'artist_msid': '1',
                        'artist_mbids': '1',
                        'listen_count': 2
                    }],
                        'user2': [{
                        'artist_name': 'artist1',
                        'artist_msid': '1',
                        'artist_mbids': '1',
                        'listen_count': 1  
                    }]
                     }
                        
        self.assertDictEqual(user.utils.get_artists('table'), dictionary)
        self.assertEqual(user.utils.get_artists('table')['user1'][0]['listen_count'], 2)
    
    def test_get_recordings(self):
        df = self.create_df()
        df.createOrReplaceTempView('table')
        dictionary =  {
                    'user1' : [{
                        'track_name': 'test',
                        'recording_msid': '1',
                        'recording_mbid': '1',
                        'artist_name': 'artist1',
                        'artist_msid': '1',
                        'artist_mbids': '1',
                        'release_name': 'test',
                        'release_msid': '1',
                        'release_mbid': '1',
                        'listen_count': 2
                    }],
                    'user2' : [{
                        'track_name': 'test',
                        'recording_msid': '1',
                        'recording_mbid': '1',
                        'artist_name': 'artist1',
                        'artist_msid': '1',
                        'artist_mbids': '1',
                        'release_name': 'test',
                        'release_msid': '1',
                        'release_mbid': '1',
                        'listen_count': 1
                    }]
                     }
                    
        self.assertDictEqual(user.utils.get_recordings('table'), dictionary)
        self.assertEqual(user.utils.get_recordings('table')['user1'][0]['listen_count'], 2)
    
    def test_get_releases(self):
        df = self.create_df()
        df.createOrReplaceTempView('table')
        dictionary =  {
                    'user1' : [{
                        'artist_name': 'artist1',
                        'artist_msid': '1',
                        'artist_mbids': '1',
                        'release_name': 'test',
                        'release_msid': '1',
                        'release_mbid': '1',
                        'listen_count': 2
                    }],
                    'user2' : [{
                        'artist_name': 'artist1',
                        'artist_msid': '1',
                        'artist_mbids': '1',
                        'release_name': 'test',
                        'release_msid': '1',
                        'release_mbid': '1',
                        'listen_count': 1
                    }]
                     }
                    
        self.assertDictEqual(user.utils.get_releases('table'), dictionary)
        self.assertEqual(user.utils.get_releases('table')['user1'][0]['listen_count'], 2)
        