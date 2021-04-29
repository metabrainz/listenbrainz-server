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
        db_user.create(1, 'testspotifyuser')
        self.user = db_user.get(1)
        db_oauth.save_token(
            user_id=1,
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )

    def test_get_active_users_to_process(self):
        db_user.create(2, 'newspotifyuser')
        db_oauth.save_token(
            user_id=2,
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        users = db_spotify.get_active_users_to_process()
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['user_id'], 1)
        self.assertEqual(users[0]['musicbrainz_row_id'], 1)
        self.assertEqual(users[1]['user_id'], 2)
        self.assertEqual(users[1]['musicbrainz_row_id'], 2)

        # check order, the users should be sorted by latest_listened_at timestamp
        db_user.create(3, 'newnewspotifyuser')
        db_oauth.save_token(
            user_id=3,
            service=ExternalServiceType.SPOTIFY,
            access_token='tokentoken',
            refresh_token='newrefresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        t = int(time.time())
        db_import.update_latest_listened_at(2, ExternalServiceType.SPOTIFY, t + 20)
        db_import.update_latest_listened_at(1, ExternalServiceType.SPOTIFY, t + 10)
        users = db_spotify.get_active_users_to_process()
        self.assertEqual(len(users), 3)
        self.assertEqual(users[0]['user_id'], 2)
        self.assertEqual(users[1]['user_id'], 1)
        self.assertEqual(users[2]['user_id'], 3)

        db_import.add_update_error(2, ExternalServiceType.SPOTIFY, 'something broke')
        db_import.add_update_error(3, ExternalServiceType.SPOTIFY, 'oops.')
        users = db_spotify.get_active_users_to_process()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['user_id'], 1)

    def test_get_user_import_details(self):
        user = db_spotify.get_user_import_details(self.user['id'])
        self.assertEqual(user['user_id'], self.user['id'])
        self.assertIn('last_updated', user)
        self.assertIn('latest_listened_at', user)
        self.assertIn('error_message', user)
