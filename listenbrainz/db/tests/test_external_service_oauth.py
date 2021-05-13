import time

from data.model.external_service import ExternalServiceType
from listenbrainz.db.testing import DatabaseTestCase

import listenbrainz.db.user as db_user
import listenbrainz.db.spotify as db_spotify
import listenbrainz.db.external_service_oauth as db_oauth


class OAuthDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(OAuthDatabaseTestCase, self).setUp()
        db_user.create(1, 'testspotifyuser')
        self.user = db_user.get(1)
        db_oauth.save_token(
            user_id=self.user['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )

    def test_create_oauth(self):
        db_user.create(2, 'spotify')
        db_oauth.save_token(
            user_id=2,
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        user = db_oauth.get_token(2, ExternalServiceType.SPOTIFY)
        self.assertEqual('token', user['access_token'])

    def test_update_token(self):
        db_oauth.update_token(
            user_id=self.user['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='testtoken',
            refresh_token='refreshtesttoken',
            expires_at=int(time.time()),
        )
        spotify_user = db_oauth.get_token(self.user['id'], ExternalServiceType.SPOTIFY)
        self.assertEqual(spotify_user['access_token'], 'testtoken')
        self.assertEqual(spotify_user['refresh_token'], 'refreshtesttoken')

    def test_get_oauth(self):
        user = db_oauth.get_token(self.user['id'], ExternalServiceType.SPOTIFY)
        self.assertEqual(user['user_id'], self.user['id'])
        self.assertEqual(user['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(user['musicbrainz_row_id'], self.user['musicbrainz_row_id'])
        self.assertEqual(user['access_token'], 'token')
        self.assertEqual(user['refresh_token'], 'refresh_token')
        self.assertIn('token_expires', user)

    def test_delete_token_unlink(self):
        db_oauth.delete_token(self.user['id'], ExternalServiceType.SPOTIFY, remove_import_log=True)
        self.assertIsNone(db_oauth.get_token(self.user['id'], ExternalServiceType.SPOTIFY))
        self.assertIsNone(db_spotify.get_user_import_details(self.user['id']))

    def test_delete_token_retain_error(self):
        db_oauth.delete_token(self.user['id'], ExternalServiceType.SPOTIFY, remove_import_log=False)
        self.assertIsNone(db_oauth.get_token(self.user['id'], ExternalServiceType.SPOTIFY))
        self.assertIsNotNone(db_spotify.get_user_import_details(self.user['id']))
