import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording

from datetime import datetime, timezone
from listenbrainz.db.testing import DatabaseTestCase

from data.model.user_cf_recommendations_recording_message import UserRecommendationsJson


class CFRecordingRecommendationDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'vansika')

    def test_insert_user_recommendation(self):
        top_artist_recording_mbids = [
            {
                'recording_mbid': 'a36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 2.3,
                'latest_listened_at': "2021-12-17T05:32:11.000Z"
            },
            {
                'recording_mbid': 'b36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 3.0,
                'latest_listened_at': None
            }
        ]

        similar_artist_recording_mbids = [
            {
                'recording_mbid': 'c36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 1.9,
                'latest_listened_at': "2020-11-14T06:21:02.000Z"
            },
            {
                'recording_mbid': 'd36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 7.6,
                'latest_listened_at': None
            }
        ]

        db_recommendations_cf_recording.insert_user_recommendation(
            self.user['id'],
            UserRecommendationsJson(**{
                'top_artist': top_artist_recording_mbids,
                'similar_artist': similar_artist_recording_mbids
            })
        )

        result = db_recommendations_cf_recording.get_user_recommendation(self.user['id'])
        self.assertEqual(getattr(result, 'recording_mbid').dict()['top_artist'], top_artist_recording_mbids)
        self.assertEqual(getattr(result, 'recording_mbid').dict()['similar_artist'], similar_artist_recording_mbids)
        self.assertGreater(int(getattr(result, 'created').strftime('%s')), 0)

    def insert_test_data(self):
        top_artist_recording_mbids = [
            {
                'recording_mbid': '17009e7b-11cb-46fa-9a42-e72937d05ee5',
                'score': 1.0,
                'latest_listened_at': "2019-10-12T09:43:57.000Z"
            },
            {
                'recording_mbid': 'c8f2edaa-6da8-471a-8c45-069852176104',
                'score': 8.7,
                'latest_listened_at': None
            }
        ]

        similar_artist_recording_mbids = [
            {
                'recording_mbid': '81925173-6863-44c3-afd8-e1023b69969d',
                'score': 2.6,
                'latest_listened_at': None
            },
            {
                'recording_mbid': '62413d46-6bac-4bad-96b9-1b062da236a2',
                'score': 3.7,
                'latest_listened_at': "2021-12-17T05:32:11.000Z"
            }
        ]

        db_recommendations_cf_recording.insert_user_recommendation(
            self.user['id'],
            UserRecommendationsJson(**{
                'top_artist': top_artist_recording_mbids,
                'similar_artist': similar_artist_recording_mbids
            })
        )

        return {
            'top_artist_recording_mbids': top_artist_recording_mbids,
            'similar_artist_recording_mbids': similar_artist_recording_mbids,
        }

    def test_get_user_recommendation(self):
        data_inserted = self.insert_test_data()

        data_received = db_recommendations_cf_recording.get_user_recommendation(self.user['id'])
        self.assertEqual(
            getattr(data_received, 'recording_mbid').dict()['top_artist'],
            data_inserted['top_artist_recording_mbids']
        )
        self.assertEqual(
            getattr(data_received, 'recording_mbid').dict()['similar_artist'],
            data_inserted['similar_artist_recording_mbids']
        )

    def test_get_timestamp_for_last_recording_recommended(self):
        ts = datetime.now(timezone.utc)
        self.insert_test_data()
        received_ts = db_recommendations_cf_recording.get_timestamp_for_last_recording_recommended()
        self.assertGreaterEqual(received_ts, ts)
