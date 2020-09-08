import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from data.model.sitewide_artist_stat import (SitewideArtistRecord,
                                             SitewideArtistStatJson,
                                             SitewideArtistStatRange)
from data.model.user_artist_stat import (UserArtistRecord, UserArtistStatJson,
                                         UserArtistStatRange)
from data.model.user_daily_activity import (UserDailyActivityRecord,
                                            UserDailyActivityStatJson,
                                            UserDailyActivityStatRange)
from data.model.user_listening_activity import (UserListeningActivityRecord,
                                                UserListeningActivityStatJson,
                                                UserListeningActivityStatRange)

from data.model.user_artist_stat import (UserArtistRecord,
                                         UserArtistStatJson,
                                         UserArtistStatRange)

from data.model.user_missing_musicbrainz_data import (UserMissingMusicBrainzDataRecord,
                                                      UserMissingMusicBrainzDataJson,
                                                      UserMissingMusicBrainzData)

from flask import current_app

from listenbrainz.spark.handlers import (
    handle_candidate_sets, handle_dataframes, handle_dump_imported,
    handle_model, handle_recommendations, handle_sitewide_entity,
    handle_user_daily_activity, handle_user_entity,
    handle_user_listening_activity,
    is_new_user_stats_batch, notify_artist_relation_import,
    notify_mapping_import,
    handle_missing_musicbrainz_data,
    notify_cf_recording_recommendations_generation)

from listenbrainz.webserver import create_app


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
            'stats_range': 'all_time',
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

    @mock.patch('listenbrainz.spark.handlers.db_stats.insert_user_listening_activity')
    @mock.patch('listenbrainz.spark.handlers.db_user.get_by_mb_id')
    @mock.patch('listenbrainz.spark.handlers.is_new_user_stats_batch')
    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_user_listening_activity(self, mock_send_mail, mock_new_user_stats, mock_get_by_mb_id, mock_db_insert):
        data = {
            'musicbrainz_id': 'iliekcomputers',
            'type': 'listening_activity',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'listening_activity': [{
                'from_ts': 1,
                'to_ts': 5,
                'time_range': '2020',
                'listen_count': 200,
            }],
        }
        mock_get_by_mb_id.return_value = {'id': 1, 'musicbrainz_id': 'iliekcomputers'}
        mock_new_user_stats.return_value = True

        with self.app.app_context():
            current_app.config['TESTING'] = False  # set testing to false to check the notifications
            handle_user_listening_activity(data)

        mock_db_insert.assert_called_with(1, UserListeningActivityStatJson(
            week=None,
            year=None,
            month=None,
            all_time=UserListeningActivityStatRange(
                to_ts=10,
                from_ts=1,
                listening_activity=[
                    UserListeningActivityRecord(
                        from_ts=1,
                        to_ts=5,
                        time_range='2020',
                        listen_count=200
                    )
                ]
            )
        ))
        mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.db_stats.insert_user_daily_activity')
    @mock.patch('listenbrainz.spark.handlers.db_user.get_by_mb_id')
    @mock.patch('listenbrainz.spark.handlers.is_new_user_stats_batch')
    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_user_daily_activity(self, mock_send_mail, mock_new_user_stats, mock_get_by_mb_id, mock_db_insert):
        data = {
            'musicbrainz_id': 'iliekcomputers',
            'type': 'daily_activity',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'daily_activity': [{
                'day': 'Monday',
                'hour': 20,
                'listen_count': 20,
            }],
        }
        mock_get_by_mb_id.return_value = {'id': 1, 'musicbrainz_id': 'iliekcomputers'}
        mock_new_user_stats.return_value = True

        with self.app.app_context():
            current_app.config['TESTING'] = False  # set testing to false to check the notifications
            handle_user_daily_activity(data)

        mock_db_insert.assert_called_with(1, UserDailyActivityStatJson(
            week=None,
            year=None,
            month=None,
            all_time=UserDailyActivityStatRange(
                to_ts=10,
                from_ts=1,
                daily_activity=[
                    UserDailyActivityRecord(
                        day='Monday',
                        hour=20,
                        listen_count=20,
                    )
                ]
            )
        ))
        mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.db_stats.insert_sitewide_artists')
    @mock.patch('listenbrainz.spark.handlers.is_new_user_stats_batch')
    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_user_daily_activity(self, mock_send_mail, mock_new_user_stats, mock_db_insert):
        data = {
            'type': 'sitewide_entity',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'entity': 'artists',
            'data': [
                {
                    'time_range': 'Monday',
                    'from_ts': 1,
                    'to_ts': 2,
                    'artists': [
                        {
                            'artist_name': 'Coldplay',
                            'artist_mbid': [],
                            'artist_msid': None,
                            'listen_count': 20
                        }
                    ]
                }
            ],
        }

        with self.app.app_context():
            current_app.config['TESTING'] = False  # set testing to false to check the notifications
            handle_sitewide_entity(data)

        mock_db_insert.assert_called_with('all_time', SitewideArtistStatJson(
            to_ts=10,
            from_ts=1,
            time_ranges=[SitewideArtistStatRange(
                time_range="Monday",
                from_ts=1,
                to_ts=2,
                artists=[SitewideArtistRecord(
                    artist_name='Coldplay',
                    artist_mbid=[],
                    artist_msid=None,
                    listen_count=20,
                )]
            )]
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
    @unittest.skip("skip temporarily")
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

    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_notify_cf_recording_recommendations_generation(self, mock_send_mail):
        with self.app.app_context():
            active_user_count = 10
            top_artist_user_count = 5
            similar_artist_user_count = 4
            total_time = datetime.now()

            # testing, should not send a mail
            self.app.config['TESTING'] = True
            notify_cf_recording_recommendations_generation({
                'active_user_count': active_user_count,
                'top_artist_user_count': top_artist_user_count,
                'similar_artist_user_count': similar_artist_user_count,
                'total_time': str(total_time)
            })
            mock_send_mail.assert_not_called()

            # in prod now, should send it
            self.app.config['TESTING'] = False
            notify_cf_recording_recommendations_generation({
                'active_user_count': active_user_count,
                'top_artist_user_count': top_artist_user_count,
                'similar_artist_user_count': similar_artist_user_count,
                'total_time': str(total_time)
            })
            mock_send_mail.assert_called_once()

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

    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_notify_mapping_import(self, mock_send_mail):
        with self.app.app_context():
            time = datetime.now()
            mapping_name = 'msid-mbid-mapping-with-matchable-20200603-202731.tar.bz2'

            # testing, should not send a mail
            self.app.config['TESTING'] = True
            notify_mapping_import({
                'imported_mapping': mapping_name,
                'time': str(time),
            })
            mock_send_mail.assert_not_called()

            # in prod now, should send it
            self.app.config['TESTING'] = False
            notify_mapping_import({
                'imported_mapping': mapping_name,
                'time': str(time),
            })
            mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_notify_artist_relation_import(self, mock_send_mail):
        with self.app.app_context():
            time = datetime.now()
            artist_relation_name = 'artist-credit-artist-credit-relations-01-20191230-134806.tar.bz2'

            # testing, should not send a mail
            self.app.config['TESTING'] = True
            notify_artist_relation_import({
                'import_artist_relation': artist_relation_name,
                'time': str(time),
            })
            mock_send_mail.assert_not_called()

            # in prod now, should send it
            self.app.config['TESTING'] = False
            notify_artist_relation_import({
                'import_artist_relation': artist_relation_name,
                'time': str(time),
            })
            mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data')
    @mock.patch('listenbrainz.spark.handlers.db_user.get_by_mb_id')
    def test_handle_missing_musicbrainz_data(self, mock_get_by_mb_id, mock_db_insert):
        data = {
            'type': 'missing_musicbrainz_data',
            'musicbrainz_id': 'vansika',
            'missing_musicbrainz_data': [
                {
                    "artist_msid": "f26d35e3-5fdd-43cf-8b94-71936451bc07",
                    "artist_name": "Katty Peri",
                    "listened_at": "2020-04-29 23:56:23",
                    "recording_msid": "568eeea3-9255-4878-9df8-296043344e04",
                    "release_msid": "8c5ba30c-4851-48fd-ac02-1b194cdb34d1",
                    "release_name": "No Place Is Home",
                    "track_name": "How High"
                }
            ],
            'source': 'cf'
        }

        mock_get_by_mb_id.return_value = {'id': 1, 'musicbrainz_id': 'vansika'}

        with self.app.app_context():
            handle_missing_musicbrainz_data(data)

        mock_db_insert.assert_called_with(1, UserMissingMusicBrainzDataJson(
            missing_musicbrainz_data=[UserMissingMusicBrainzDataRecord(
                artist_msid="f26d35e3-5fdd-43cf-8b94-71936451bc07",
                artist_name="Katty Peri",
                listened_at="2020-04-29 23:56:23",
                recording_msid="568eeea3-9255-4878-9df8-296043344e04",
                release_msid="8c5ba30c-4851-48fd-ac02-1b194cdb34d1",
                release_name="No Place Is Home",
                track_name="How High"
            )]),
            'cf'
        )
