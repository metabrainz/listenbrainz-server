import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording

from datetime import datetime, timezone
from listenbrainz.db.testing import DatabaseTestCase

from data.model.user_cf_recommendations_recording_message import UserRecommendationsJson


class CFRecordingRecommendationDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(self.db_conn, 1, 'vansika')

    def test_insert_user_recommendation(self):
        raw_recording_mbids = [
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

        db_recommendations_cf_recording.insert_user_recommendation(
            self.db_conn,
            self.user['id'],
            UserRecommendationsJson(**{
                'raw': raw_recording_mbids,
            })
        )

        result = db_recommendations_cf_recording.get_user_recommendation(self.db_conn, self.user['id'])
        self.assertEqual(getattr(result, 'recording_mbid').dict()['raw'], raw_recording_mbids)
        self.assertGreater(int(getattr(result, 'created').strftime('%s')), 0)

    def insert_test_data(self):
        raw_recording_mbids = [
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

        db_recommendations_cf_recording.insert_user_recommendation(
            self.db_conn,
            self.user['id'],
            UserRecommendationsJson(**{
                'raw': raw_recording_mbids,
            })
        )

        return {
            'raw_recording_mbids': raw_recording_mbids,
        }

    def test_get_user_recommendation(self):
        data_inserted = self.insert_test_data()

        data_received = db_recommendations_cf_recording.get_user_recommendation(self.db_conn, self.user['id'])
        self.assertEqual(
            getattr(data_received, 'recording_mbid').dict()['raw'],
            data_inserted['raw_recording_mbids']
        )

    def test_get_timestamp_for_last_recording_recommended(self):
        # get_or_create starts a transaction, and NOW() uses that value in insert so need to commit here so that
        # the insert starts a new transaction
        self.db_conn.commit()
        ts = datetime.now(timezone.utc)
        self.insert_test_data()
        received_ts = db_recommendations_cf_recording.get_timestamp_for_last_recording_recommended(self.db_conn)
        self.assertGreaterEqual(received_ts, ts)
