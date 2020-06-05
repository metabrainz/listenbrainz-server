import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from flask import current_app

from listenbrainz.spark.handlers import (
    handle_candidate_sets, handle_dataframes, handle_dump_imported,
    handle_model, handle_recommendations, handle_user_entity,
    is_new_cf_recording_recommendation_batch, is_new_user_stats_batch)
from listenbrainz.webserver import create_app

from listenbrainz.db.model.user_artist_stat import UserArtistStatJson, UserArtistStatRange, UserArtistRecord


class HandlersTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()

    @mock.patch('listenbrainz.spark.handlers.db_stats.insert_user_artists')
    @mock.patch('listenbrainz.spark.handlers.db_user.get_by_mb_id')
    @mock.patch('listenbrainz.spark.handlers.is_new_user_stats_batch')
    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_user_entity(self, mock_send_mail, mock_new_user_stats, mock_get_by_mb_id, mock_db_insert):
        data = {
            'musicbrainz_id': 'iliekcomputers',
            'type': 'user_entity',
            'entity': 'artists',
            'range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'count': 1,
            'data': [{
                'artist_name': 'Kanye West',
                'listen_count': 200,
            }],
        }
        mock_get_by_mb_id.return_value = {'id': 1, 'musicbrainz_id': 'iliekcomputers'}
        mock_new_user_stats.return_value = True

        with self.app.app_context():
            current_app.config['TESTING'] = False  # set testing to false to check the notifications
            handle_user_entity(data)

        mock_db_insert.assert_called_with(1, UserArtistStatJson(
            week=None,
            year=None,
            month=None,
            all_time=UserArtistStatRange(
                to_ts=10,
                from_ts=1,
                count=1,
                artists=[
                    UserArtistRecord(
                        artist_msid=None,
                        artist_mbids=[],
                        listen_count=200,
                        artist_name='Kanye West',
                    )
                ]
            )
        ))
        mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.db_stats.get_timestamp_for_last_user_stats_update')
    def test_is_new_user_stats_batch(self, mock_db_get_timestamp):
        mock_db_get_timestamp.return_value = datetime.now(timezone.utc)
        self.assertFalse(is_new_user_stats_batch())
        mock_db_get_timestamp.return_value = datetime.now(timezone.utc) - timedelta(minutes=21)
        self.assertTrue(is_new_user_stats_batch())

    @mock.patch('listenbrainz.spark.handlers.db_recommendations_cf_recording.insert_user_recommendation')
    @mock.patch('listenbrainz.spark.handlers.db_user.get_by_mb_id')
    @mock.patch('listenbrainz.spark.handlers.is_new_cf_recording_recommendation_batch')
    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_recommendations(self, mock_send_mail, mock_new_recommendation, mock_get_by_mb_id, mock_db_insert):
        data = {
            'musicbrainz_id': 'vansika',
            'type': 'cf_recording_recommendations',
            'top_artist': ['a36d6fc9-49d0-4789-a7dd-a2b72369ca45'],
            'similar_artist': ['b36d6fc9-49d0-4789-a7dd-a2b72369ca45'],
        }

        mock_get_by_mb_id.return_value = {'id': 1, 'musicbrainz_id': 'vansika'}
        mock_new_recommendation.return_value = True

        with self.app.app_context():
            current_app.config['TESTING'] = False
            handle_recommendations(data)

        mock_db_insert.assert_called_with(1, data['top_artist'], data['similar_artist'])
        mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.db_recommendations_cf_recording.get_timestamp_for_last_recording_recommended')
    def test_is_new_cf_recording_recommendation_batch(self, mock_db_get_timestamp):
        mock_db_get_timestamp.return_value = datetime.now(timezone.utc)
        self.assertFalse(is_new_cf_recording_recommendation_batch())
        mock_db_get_timestamp.return_value = datetime.now(timezone.utc) - timedelta(days=8)
        self.assertTrue(is_new_cf_recording_recommendation_batch())

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

    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_dataframes(self, mock_send_mail):
        with self.app.app_context():
            time = datetime.utcnow()

            self.app.config['TESTING'] = True
            handle_dataframes({
                'type': 'cf_recording_dataframes',
                'dataframe_upload_time': str(time),
                'total_time': '3.1',
                'from_date': str(time.strftime('%b %Y')),
                'to_date': str(time.strftime('%b %Y')),
            })
            mock_send_mail.assert_not_called()

            self.app.config['TESTING'] = False
            handle_dataframes({
                'type': 'cf_recording_dataframes',
                'dataframe_upload_time': str(time),
                'total_time': '3.1',
                'from_date': str(time.strftime('%b %Y')),
                'to_date': str(time.strftime('%b %Y')),
            })
            mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_model(self, mock_send_mail):
        with self.app.app_context():
            time = datetime.utcnow()

            self.app.config['TESTING'] = True
            handle_model({
                'type': 'cf_recording_model',
                'model_upload_time': str(time),
                'total_time': '3.1',
            })
            mock_send_mail.assert_not_called()

            self.app.config['TESTING'] = False
            handle_model({
                'type': 'cf_recording_model',
                'model_upload_time': str(time),
                'total_time': '3.1',
            })
            mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_candidate_sets(self, mock_send_mail):
        with self.app.app_context():
            time = datetime.utcnow()

            self.app.config['TESTING'] = True
            handle_candidate_sets({
                'type': 'cf_recording_candidate_sets',
                'candidate_sets_upload_time': str(time),
                'total_time': '3.1',
                'from_date': str(time),
                'to_date': str(time)
            })
            mock_send_mail.assert_not_called()

            self.app.config['TESTING'] = False
            handle_candidate_sets({
                'type': 'cf_recording_candidate_sets',
                'candidate_sets_upload_time': str(time),
                'total_time': '3.1',
                'from_date': str(time),
                'to_date': str(time)
            })
            mock_send_mail.assert_called_once()
