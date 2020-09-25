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
                'score': 2.3
            },
            {
                'recording_mbid':'b36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 3.0
            }
        ]

        similar_artist_recording_mbids = [
            {
                'recording_mbid': 'c36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 1.9
            },
            {
                'recording_mbid': 'd36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 7.6
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
                'recording_mbid': 'x36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 1.0
            },
            {
                'recording_mbid': 'h36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 8.7
            }
        ]

        similar_artist_recording_mbids = [
            {
                'recording_mbid': 'v36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 2.6
            },
            {
                'recording_mbid': 'i36d6fc9-49d0-4789-a7dd-a2b72369ca45',
                'score': 3.7
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
        self.assertEqual(getattr(data_received, 'recording_mbid').dict()['top_artist'], data_inserted['top_artist_recording_mbids'])
        self.assertEqual(getattr(data_received, 'recording_mbid').dict()['similar_artist'], data_inserted['similar_artist_recording_mbids'])

    def test_get_timestamp_for_last_recording_recommended(self):
        ts = datetime.now(timezone.utc)
        self.insert_test_data()
        received_ts = db_recommendations_cf_recording.get_timestamp_for_last_recording_recommended()
        self.assertGreaterEqual(received_ts, ts)
