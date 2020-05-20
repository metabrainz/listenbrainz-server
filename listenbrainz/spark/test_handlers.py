import unittest

from datetime import datetime, timezone, timedelta
from flask import current_app
from listenbrainz.spark.handlers import handle_user_artist, is_new_user_stats_batch, handle_dump_imported
from listenbrainz.webserver import create_app
from unittest import mock


class HandlersTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()

    @mock.patch('listenbrainz.spark.handlers.db_stats.insert_user_stats')
    @mock.patch('listenbrainz.spark.handlers.db_user.get_by_mb_id')
    @mock.patch('listenbrainz.spark.handlers.is_new_user_stats_batch')
    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_user_artist(self, mock_send_mail, mock_new_user_stats, mock_get_by_mb_id, mock_db_insert):
        data = {
            'musicbrainz_id': 'iliekcomputers',
            'type': 'user_artist',
            'artists': [{'artist_name': 'Kanye West', 'count': 200}],
        }
        mock_get_by_mb_id.return_value = {'id': 1, 'musicbrainz_id': 'iliekcomputers'}
        mock_new_user_stats.return_value = True

        with self.app.app_context():
            current_app.config['TESTING'] = False  # set testing to false to check the notifications
            handle_user_artist(data)

        mock_db_insert.assert_called_with(1, {'artists': data['artists']}, {}, {})
        mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.db_stats.get_timestamp_for_last_user_stats_update')
    def test_is_new_user_stats_batch(self, mock_db_get_timestamp):
        mock_db_get_timestamp.return_value = datetime.now(timezone.utc)
        self.assertFalse(is_new_user_stats_batch())
        mock_db_get_timestamp.return_value = datetime.now(timezone.utc) - timedelta(hours=13)
        self.assertTrue(is_new_user_stats_batch())

    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_dump_imported(self, mock_send_mail):
        with self.app.app_context():
            time = datetime.now()
            dump_name = 'listenbrainz-listens-dump-20200223-000000-spark-full.tar.xz'

            # testing, should not send a mail
            self.app.config['TESTING'] = True
            handle_dump_imported({
                'imported_dump': dump_name,
                'time': str(time),
            })
            mock_send_mail.assert_not_called()

            # in prod now, should send it
            self.app.config['TESTING'] = False
            handle_dump_imported({
                'imported_dump': dump_name,
                'time': str(time),
            })
            mock_send_mail.assert_called_once()
