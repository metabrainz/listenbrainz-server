import os
import json
import time

import listenbrainz.webserver
from datetime import datetime

import listenbrainz.db.user as db_user
from data.model.external_service import ExternalServiceType
from listenbrainz.domain.external_service import ExternalServiceAPIError, \
    ExternalServiceInvalidGrantError
from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.listens_importer.spotify import SpotifyImporter
from unittest.mock import patch
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import external_service_oauth as db_oauth


class ConvertListensTestCase(DatabaseTestCase):

    def setUp(self):
        super(ConvertListensTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, 'testuserpleaseignore')

        self.DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh',
                            token_expires_ts=int(time.time()) + 1000, record_listens=True,
                            scopes=['user-read-recently-played'])

    def test_parse_play_to_listen_no_isrc(self):
        data = json.load(open(os.path.join(self.DATA_DIR, 'spotify_play_no_isrc.json')))

        with listenbrainz.webserver.create_app().app_context():
            importer = SpotifyImporter()
            listen = importer.convert_spotify_recent_play_to_listen(data)[0]

        expected_listen = {
            'listened_at': 1519241031.761,
            'track_metadata': {
                'artist_name': 'The Hollies',
                'track_name': "Draggin' My Heels - Special Disco Version",
                'release_name': 'Down To The Sea And Back: The Continuing Journey Of The Balearic Beat. Volume 1.',
                'additional_info': {
                    'tracknumber': 10,
                    'discnumber': 1,
                    'spotify_artist_ids': ['https://open.spotify.com/artist/6waa8mKu91GjzD4NlONlNJ'],
                    'artist_names': ['The Hollies'],
                    'duration_ms': 392080,
                    'spotify_album_id': 'https://open.spotify.com/album/2XoKFlFYe5Cy2Zt8gSHsWH',
                    'release_artist_name': 'The San Sebastian Strings',
                    'release_artist_names': ['The San Sebastian Strings'],
                    'spotify_album_artist_ids': ['https://open.spotify.com/artist/5SPV5qSO1UNNwwBCzrNfum'],
                    'spotify_id': 'https://open.spotify.com/track/5SvAa2E5qyvZzfFlVtnXsQ',
                    'origin_url': 'https://open.spotify.com/track/5SvAa2E5qyvZzfFlVtnXsQ',
                    'submission_client': 'listenbrainz',
                    'music_service': 'spotify.com'
                }
            }
        }

        self.assertDictEqual(listen, expected_listen)

    def test_parse_play_to_listen_many_artists(self):
        self.maxDiff = None

        # If a spotify play record has many artists, make sure they are appended
        data = json.load(open(os.path.join(self.DATA_DIR, 'spotify_play_two_artists.json')))

        with listenbrainz.webserver.create_app().app_context():
            importer = SpotifyImporter()
            listen = importer.convert_spotify_recent_play_to_listen(data)[0]

        expected_listen = {
            'listened_at': 1519240503.665,
            'track_metadata': {
                'artist_name': 'Robert Plant, Alison Krauss',
                'track_name': 'Rich Woman',
                'release_name': 'Raising Sand',
                'additional_info': {
                    'tracknumber': 1,
                    'discnumber': 1,
                    'isrc': 'USRO20707501',
                    'spotify_artist_ids': ['https://open.spotify.com/artist/1OwarW4LEHnoep20ixRA0y',
                                           'https://open.spotify.com/artist/5J6L7N6B4nI1M5cwa29mQG'],
                    'artist_names': ['Robert Plant', 'Alison Krauss'],
                    'duration_ms': 243480,
                    'spotify_album_id': 'https://open.spotify.com/album/3Z5nkL4z2Tsa3b79vv6LXb',
                    'release_artist_name': 'Robert Plant, Alison Krauss',
                    'release_artist_names': ['Robert Plant', 'Alison Krauss'],
                    'spotify_album_artist_ids': ['https://open.spotify.com/artist/1OwarW4LEHnoep20ixRA0y',
                                                 'https://open.spotify.com/artist/5J6L7N6B4nI1M5cwa29mQG'],
                    'spotify_id': 'https://open.spotify.com/track/6bnmRsdxYacqLSlS36EJT6',
                    'origin_url': 'https://open.spotify.com/track/6bnmRsdxYacqLSlS36EJT6',
                    'submission_client': 'listenbrainz',
                    'music_service': 'spotify.com'
                }
            }
        }

        self.assertDictEqual(listen, expected_listen)

    @patch('listenbrainz.listens_importer.base.send_notification')
    def test_notify_user(self, mock_send_notification):
        db_user.create(self.db_conn, 2, "two", "one@two.one")
        app = listenbrainz.webserver.create_app()
        app.config['SERVER_NAME'] = "test"
        with app.app_context():
            importer = SpotifyImporter()
            importer.notify_error(musicbrainz_id="two", error='some random error')
        mock_send_notification.assert_called_once()
        self.assertEqual(mock_send_notification.call_args[1]['user_email'], 'one@two.one')

    @patch('listenbrainz.domain.spotify.SpotifyService.update_user_import_status')
    @patch.object(SpotifyImporter, 'notify_error')
    @patch.object(SpotifyImporter, 'make_api_request')
    def test_notification_on_api_error(self, mock_make_api_request, mock_notify_error, mock_update):
        mock_make_api_request.side_effect = ExternalServiceAPIError('api borked')
        app = listenbrainz.webserver.create_app()
        app.config['TESTING'] = False
        with app.app_context():
            importer = SpotifyImporter()
            importer.process_all_users()
            mock_notify_error.assert_called_once_with(self.user['musicbrainz_id'], 'api borked')
            mock_update.assert_called_once()

    @patch('spotipy.Spotify')
    def test_spotipy_methods_are_called_with_correct_params(self, mock_spotipy):
        mock_spotipy.return_value.current_user_playing_track.return_value = None

        with listenbrainz.webserver.create_app().app_context():
            SpotifyService().update_latest_listen_ts(self.user['id'],
                                                     int(datetime(2014, 5, 13, 16, 53, 20).timestamp()))
            importer = SpotifyImporter()
            importer.process_all_users()
            mock_spotipy.return_value.current_user_playing_track.assert_called_once()
            mock_spotipy.return_value.current_user_recently_played.assert_called_once_with(limit=50, after=1400000000000)

    @patch('spotipy.Spotify.current_user_recently_played')
    @patch('spotipy.Spotify.current_user_playing_track')
    def test_spotipy_methods_are_called_with_correct_params_with_no_latest_listened_at(self, mock_current_user_playing_track, mock_current_user_recently_played):
        mock_current_user_playing_track.return_value = None
        mock_current_user_recently_played.return_value = None

        with listenbrainz.webserver.create_app().app_context():
            importer = SpotifyImporter()
            importer.process_all_users()
            mock_current_user_playing_track.assert_called_once()
            mock_current_user_recently_played.assert_called_once_with(limit=50, after=0)

    @patch('listenbrainz.domain.spotify.SpotifyService.refresh_user_token')
    def process_one_user(self, mock_refresh_user_token):
        mock_refresh_user_token.side_effect = ExternalServiceInvalidGrantError
        expired_token_spotify_user = dict(
            user_id=1,
            musicbrainz_id='spotify_user',
            musicbrainz_row_id=312,
            access_token='old-token',
            token_expires=int(time.time()),
            refresh_token='old-refresh-token',
            last_updated=None,
            latest_listened_at=None,
            scopes=['user-read-recently-played'],
        )
        with (self.assertRaises(ExternalServiceInvalidGrantError),
              listenbrainz.webserver.create_app().app_context()):
            importer = SpotifyImporter()
            importer.process_one_user(expired_token_spotify_user)
