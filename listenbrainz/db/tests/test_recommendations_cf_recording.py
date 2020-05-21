import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording

from datetime import datetime, timezone
from listenbrainz.db.testing import DatabaseTestCase


class CFRecordingRecommendationDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'vansika')

    def test_insert_user_recommendation(self):
        top_artist_recording_mbids = ['a36d6fc9-49d0-4789-a7dd-a2b72369ca45, b36d6fc9-49d0-4789-a7dd-a2b72369ca45']
        similar_artist_recording_mbids = ['c36d6fc9-49d0-4789-a7dd-a2b72369ca45', 'd36d6fc9-49d0-4789-a7dd-a2b72369ca45']

        db_recommendations_cf_recording.insert_user_recommendation(
            user_id=self.user['id'],
            top_artist_recording_mbids=top_artist_recording_mbids,
            similar_artist_recording_mbids=similar_artist_recording_mbids
        )

        result = db_recommendations_cf_recording.get_user_recommendation(self.user['id'])
        self.assertEqual(result['recording_mbid']['top_artist'], top_artist_recording_mbids)
        self.assertEqual(result['recording_mbid']['similar_artist'], similar_artist_recording_mbids)
        self.assertGreater(int(result['created'].strftime('%s')), 0)

    def insert_test_data(self):
        top_artist_recording_mbids = ['x36d6fc9-49d0-4789-a7dd-a2b72369ca45, h36d6fc9-49d0-4789-a7dd-a2b72369ca45']
        similar_artist_recording_mbids = ['v36d6fc9-49d0-4789-a7dd-a2b72369ca45', 'i36d6fc9-49d0-4789-a7dd-a2b72369ca45']

        db_recommendations_cf_recording.insert_user_recommendation(
            user_id=self.user['id'],
            top_artist_recording_mbids=top_artist_recording_mbids,
            similar_artist_recording_mbids=similar_artist_recording_mbids
        )

        return {
            'top_artist_recording_mbids': top_artist_recording_mbids,
            'similar_artist_recording_mbids': similar_artist_recording_mbids,
        }

    def test_get_user_recommendation(self):
        data_inserted = self.insert_test_data()

        data_received = db_recommendations_cf_recording.get_user_recommendation(self.user['id'])
        self.assertEqual(data_received['recording_mbid']['top_artist'], data_inserted['top_artist_recording_mbids'])
        self.assertEqual(data_received['recording_mbid']['similar_artist'], data_inserted['similar_artist_recording_mbids'])

    def test_get_timestamp_for_last_recording_recommended(self):
        ts = datetime.now(timezone.utc)
        self.insert_test_data()
        received_ts = db_recommendations_cf_recording.get_timestamp_for_last_recording_recommended()
        self.assertGreaterEqual(received_ts, ts)
