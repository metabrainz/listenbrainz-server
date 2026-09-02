
import listenbrainz.db.user as db_user
import listenbrainz.db.spotify as db_spotify
import listenbrainz.db.listens_importer as db_import
import listenbrainz.db.external_service_oauth as db_oauth

import sqlalchemy
import time

from data.model.external_service import ExternalServiceType
from listenbrainz.db import listens_importer
from listenbrainz.db.testing import DatabaseTestCase


class ListensImporterDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(ListensImporterDatabaseTestCase, self).setUp()
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

    def _save_spotify_user(self, musicbrainz_row_id, musicbrainz_id):
        user = db_user.get_or_create(self.db_conn, musicbrainz_row_id, musicbrainz_id)
        db_oauth.save_token(
            self.db_conn,
            user_id=user['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        return user

    def _get_claimed_at(self, user_id):
        result = self.db_conn.execute(sqlalchemy.text("""
            SELECT claimed_at
              FROM listens_importer
             WHERE user_id = :user_id
               AND service = :service
        """), {
            "user_id": user_id,
            "service": ExternalServiceType.SPOTIFY.value,
        })
        row = result.fetchone()
        return row.claimed_at if row else None

    def test_claim_and_release_user(self):
        users = db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=1
        )
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['user_id'], self.user['id'])
        self.assertIsNotNone(self._get_claimed_at(self.user['id']))

        db_import.release_user_claim(self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY)
        self.assertIsNone(self._get_claimed_at(self.user['id']))

    def test_claim_skips_already_claimed_users(self):
        users = db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=10
        )
        self.assertEqual(len(users), 1)

        users = db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=10
        )
        self.assertEqual(len(users), 0)

        db_import.release_user_claim(self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY)
        users = db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=10
        )
        self.assertEqual(len(users), 1)

    def test_claim_excludes_paused_users(self):
        user2 = self._save_spotify_user(2, 'pausedspotifyuser')
        db_user.pause(self.db_conn, user2['id'])

        users = db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=10
        )
        self.assertEqual({user['user_id'] for user in users}, {self.user['id']})

    def test_claim_prefers_least_recently_updated(self):
        user2 = self._save_spotify_user(2, 'newspotifyuser')
        t = int(time.time())
        db_import.update_latest_listened_at(
            self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY, t
        )
        db_import.update_latest_listened_at(
            self.db_conn, user2['id'], ExternalServiceType.SPOTIFY, t
        )
        db_import.release_user_claim(self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY)

        users = db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=1
        )
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['user_id'], user2['id'])

    def test_release_user_claims_batch(self):
        user2 = self._save_spotify_user(2, 'batchspotifyuser')
        users = db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=10
        )
        self.assertEqual(len(users), 2)

        db_import.release_user_claims(
            self.db_conn,
            [self.user['id'], user2['id']],
            ExternalServiceType.SPOTIFY,
        )
        self.assertIsNone(self._get_claimed_at(self.user['id']))
        self.assertIsNone(self._get_claimed_at(user2['id']))

    def test_stale_claims_are_reclaimed(self):
        db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=1
        )
        self.db_conn.execute(sqlalchemy.text("""
            UPDATE listens_importer
               SET claimed_at = now() - interval '13 hours'
             WHERE user_id = :user_id
               AND service = :service
        """), {
            "user_id": self.user['id'],
            "service": ExternalServiceType.SPOTIFY.value,
        })
        self.db_conn.commit()

        users = db_import.claim_users_to_process(
            self.db_conn, ExternalServiceType.SPOTIFY, batch_size=1
        )
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['user_id'], self.user['id'])
        self.assertIsNotNone(self._get_claimed_at(self.user['id']))

    def test_update_status(self):
        db_import.update_status(
            self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY, "Error", 0,
            error={'message': 'test error message', 'retry': True}
        )
        spotify_user = db_spotify.get_user_import_details(self.db_conn, self.user['id'])
        self.assertEqual(spotify_user['error']['message'], 'test error message')
        self.assertEqual(spotify_user['error']['retry'], True)
        self.assertIsNotNone(spotify_user['last_updated'])

        db_import.update_status(self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY, "Synced", 0)
        spotify_user = db_spotify.get_user_import_details(self.db_conn, self.user['id'])
        self.assertIsNone(spotify_user['error'])
        self.assertIsNotNone(spotify_user['last_updated'])

    def test_update_latest_listened_at(self):
        spotify_user = db_spotify.get_user_import_details(self.db_conn, self.user['id'])
        self.assertIsNone(spotify_user['latest_listened_at'])
        self.assertIsNone(spotify_user['last_updated'])
        t = int(time.time())
        db_import.update_latest_listened_at(self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY, t)
        spotify_user = db_spotify.get_user_import_details(self.db_conn, self.user['id'])
        self.assertEqual(t, int(spotify_user['latest_listened_at'].strftime('%s')))
        self.assertIsNotNone(spotify_user['last_updated'])

    def test_update_latest_import(self):
        user = db_user.get_or_create(self.db_conn, 3, 'updatelatestimportuser')

        val = int(time.time())
        listens_importer.update_latest_listened_at(self.db_conn, user['id'], ExternalServiceType.LASTFM, val)
        status = listens_importer.get_import_status(self.db_conn, user['id'], ExternalServiceType.LASTFM)
        self.assertEqual(status["latest_listened_at"], val)

        listens_importer.update_latest_listened_at(self.db_conn, user['id'], ExternalServiceType.LASTFM, 0)
        status = listens_importer.get_import_status(self.db_conn, user['id'], ExternalServiceType.LASTFM)
        self.assertEqual(status["latest_listened_at"], 0)
