import os
import json
import listenbrainz.webserver
import time


from listenbrainz.domain.spotify import Spotify, SpotifyAPIError, SpotifyListenBrainzError
from listenbrainz.spotify_updater import spotify_read_listens
from listenbrainz.webserver.views.api_tools import LISTEN_TYPE_IMPORT
from unittest import TestCase
from unittest.mock import patch


class ConvertListensTestCase(TestCase):

    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

    def test_parse_play_to_listen_no_isrc(self):
        data = json.load(open(os.path.join(self.DATA_DIR, 'spotify_play_no_isrc.json')))

        listen = spotify_read_listens._convert_spotify_play_to_listen(data, LISTEN_TYPE_IMPORT)

        expected_listen = {
            'listened_at': 1519241031,
            'track_metadata': {
                'artist_name': 'The Hollies',
                'track_name': "Draggin' My Heels - Special Disco Version",
                'release_name': 'Down To The Sea And Back: The Continuing Journey Of The Balearic Beat. Volume 1.',
                'additional_info': {
                    'tracknumber': 10,
                    'discnumber': 1,
                    'spotify_artist_ids': ['https://open.spotify.com/artist/6waa8mKu91GjzD4NlONlNJ'],
                    'artist_names': ['The Hollies'],
                    'listening_from': 'spotify',
                    'duration_ms': 392080,
                    'spotify_album_id': 'https://open.spotify.com/album/2XoKFlFYe5Cy2Zt8gSHsWH',
                    'release_artist_name': 'The San Sebastian Strings',
                    'release_artist_names': ['The San Sebastian Strings'],
                    'spotify_album_artist_ids': ['https://open.spotify.com/artist/5SPV5qSO1UNNwwBCzrNfum'],
                    'spotify_id': 'https://open.spotify.com/track/5SvAa2E5qyvZzfFlVtnXsQ'
                }
            }
        }

        self.assertDictEqual(listen, expected_listen)

    def test_parse_play_to_listen_many_artists(self):
        self.maxDiff = None

        # If a spotify play record has many artists, make sure they are appended
        data = json.load(open(os.path.join(self.DATA_DIR, 'spotify_play_two_artists.json')))

        listen = spotify_read_listens._convert_spotify_play_to_listen(data, LISTEN_TYPE_IMPORT)

        expected_listen = {
            'listened_at': 1519240503,
            'track_metadata': {
                'artist_name': 'Robert Plant, Alison Krauss',
                'track_name': 'Rich Woman',
                'release_name': 'Raising Sand',
                'additional_info': {
                    'tracknumber': 1,
                    'discnumber': 1,
                    'isrc': 'USRO20707501',
                    'spotify_artist_ids': ['https://open.spotify.com/artist/1OwarW4LEHnoep20ixRA0y', 'https://open.spotify.com/artist/5J6L7N6B4nI1M5cwa29mQG'],
                    'artist_names': ['Robert Plant', 'Alison Krauss'],
                    'listening_from': 'spotify',
                    'duration_ms': 243480,
                    'spotify_album_id': 'https://open.spotify.com/album/3Z5nkL4z2Tsa3b79vv6LXb',
                    'release_artist_name': 'Robert Plant, Alison Krauss',
                    'release_artist_names': ['Robert Plant', 'Alison Krauss'],
                    'spotify_album_artist_ids': ['https://open.spotify.com/artist/1OwarW4LEHnoep20ixRA0y', 'https://open.spotify.com/artist/5J6L7N6B4nI1M5cwa29mQG'],
                    'spotify_id': 'https://open.spotify.com/track/6bnmRsdxYacqLSlS36EJT6'
                }
            }
        }

        self.assertDictEqual(listen, expected_listen)

    @patch('listenbrainz.spotify_updater.spotify_read_listens.send_mail')
    @patch('listenbrainz.spotify_updater.spotify_read_listens.mb_editor.get_editor_by_id')
    def test_notify_user(self, mock_get_editor, mock_send_mail):
        mock_get_editor.return_value = {'email': 'example@listenbrainz.org'}
        with listenbrainz.webserver.create_app().app_context():
            spotify_read_listens.notify_error(musicbrainz_row_id=1, error='some random error')
        mock_get_editor.assert_called_once_with(1)
        mock_send_mail.assert_called_once()
        self.assertListEqual(mock_send_mail.call_args[1]['recipients'], ['example@listenbrainz.org'])


    @patch('listenbrainz.spotify_updater.spotify_read_listens.spotify.update_last_updated')
    @patch('listenbrainz.spotify_updater.spotify_read_listens.notify_error')
    @patch('listenbrainz.spotify_updater.spotify_read_listens.process_one_user')
    @patch('listenbrainz.domain.spotify.get_active_users_to_process')
    def test_notification_on_api_error(self, mock_get_active_users, mock_process_one_user, mock_notify_error, mock_update):
        mock_process_one_user.side_effect = SpotifyAPIError('api borked')
        mock_get_active_users.return_value = [
            Spotify(
                user_id=1,
                musicbrainz_id='jude',
                musicbrainz_row_id=312,
                user_token='token',
                token_expires=int(time.time()),
                refresh_token='refresh',
                last_updated=None,
                record_listens=True,
                error_message=None,
                latest_listened_at=None,
            ),
        ]
        app = listenbrainz.webserver.create_app()
        app.config['TESTING'] = False
        with app.app_context():
            spotify_read_listens.process_all_spotify_users()
            mock_notify_error.assert_called_once_with(312, 'api borked')
            mock_update.assert_called_once()
