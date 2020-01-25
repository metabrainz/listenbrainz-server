import unittest

from unittest import mock
from listenbrainz.spark.handlers import handle_user_artist

class HandlersTestCase(unittest.TestCase):

    @mock.patch('listenbrainz.spark.handlers.db_stats.insert_user_stats')
    @mock.patch('listenbrainz.spark.handlers.db_user.get_by_mb_id')
    @mock.patch('listenbrainz.spark.handlers.current_app')
    def test_handle_user_artist(self, mock_app, mock_get_by_mb_id, mock_db_insert):
        data = {
            'musicbrainz_id': 'iliekcomputers',
            'type': 'user_artist',
            'artist_stats': [{'artist_name': 'Kanye West', 'count': 200}],
            'artist_count': 1,
        }
        mock_get_by_mb_id.return_value = {'id': 1, 'musicbrainz_id': 'iliekcomputers'}

        handle_user_artist(data)
        mock_db_insert.assert_called_with(1, data['artist_stats'], {}, {}, data['artist_count'])
