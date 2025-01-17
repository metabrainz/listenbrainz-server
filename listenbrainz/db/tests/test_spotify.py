import listenbrainz.db.user as db_user
import listenbrainz.db.spotify as db_spotify
import listenbrainz.db.listens_importer as db_import
import listenbrainz.db.external_service_oauth as db_oauth

import time

from data.model.external_service import ExternalServiceType
from listenbrainz.db.testing import DatabaseTestCase


class SpotifyDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(SpotifyDatabaseTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, 'testspotifyuser')
        db_oauth.save_token(
            self.db_conn,
            user_id=self.user['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )

    def test_get_active_users_to_process(self):
        user2 = db_user.get_or_create(self.db_conn, 2, 'newspotifyuser')
        db_oauth.save_token(
            self.db_conn,
            user_id=user2['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        users = db_import.get_active_users_to_process(self.db_conn, ExternalServiceType.SPOTIFY)
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['user_id'], self.user['id'])
        self.assertEqual(users[0]['musicbrainz_row_id'], 1)
        self.assertEqual(users[1]['user_id'], user2['id'])
        self.assertEqual(users[1]['musicbrainz_row_id'], 2)

        # check order, the users should be sorted by latest_listened_at timestamp
        user3 = db_user.get_or_create(self.db_conn, 3, 'newnewspotifyuser')
        db_oauth.save_token(
            self.db_conn,
            user_id=user3['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='tokentoken',
            refresh_token='newrefresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        t = int(time.time())
        db_import.update_latest_listened_at(self.db_conn, user2['id'], ExternalServiceType.SPOTIFY, t + 20)
        db_import.update_latest_listened_at(self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY, t + 10)
        users = db_import.get_active_users_to_process(self.db_conn, ExternalServiceType.SPOTIFY)
        self.assertEqual(len(users), 3)
        self.assertEqual(users[0]['user_id'], user2['id'])
        self.assertEqual(users[1]['user_id'], self.user['id'])
        self.assertEqual(users[2]['user_id'], user3['id'])

        db_import.update_import_status(self.db_conn, user2['id'], ExternalServiceType.SPOTIFY, 'something broke')
        db_import.update_import_status(self.db_conn, user3['id'], ExternalServiceType.SPOTIFY, 'oops.')
        users = db_import.get_active_users_to_process(self.db_conn, ExternalServiceType.SPOTIFY, True)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['user_id'], self.user['id'])

    def test_get_user_import_details(self):
        user = db_spotify.get_user_import_details(self.db_conn, self.user['id'])
        self.assertEqual(user['user_id'], self.user['id'])
        self.assertIn('last_updated', user)
        self.assertIn('latest_listened_at', user)
        self.assertIn('error_message', user)
