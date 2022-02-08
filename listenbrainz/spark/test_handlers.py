from datetime import datetime, timedelta, timezone
from unittest import mock

from flask import current_app

from data.model.common_stat import StatRange, StatRecordList, StatApi
from data.model.user_artist_stat import ArtistRecord
from data.model.user_cf_recommendations_recording_message import (UserRecommendationsJson,
                                                                  UserRecommendationsRecord)
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from data.model.user_missing_musicbrainz_data import (UserMissingMusicBrainzDataRecord,
                                                      UserMissingMusicBrainzDataJson)
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import user as db_user
from listenbrainz.db import stats as db_stats
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


class HandlersTestCase(DatabaseTestCase):

    def setUp(self):
        super(HandlersTestCase, self).setUp()
        self.app = create_app()
        db_user.create(1, 'iliekcomputers')
        db_user.create(2, 'lucifer')
        self.maxDiff = None

    def test_handle_user_entity(self):
        data = {
            'type': 'user_entity',
            'entity': 'artists',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'data': [
                {
                    'user_id': 1,
                    'data': [{
                        'artist_name': 'Kanye West',
                        'listen_count': 200,
                    }],
                    'count': 1,
                },
                {
                    'user_id': 2,
                    'data': [
                        {
                            'artist_name': 'Selena Gomez',
                            'listen_count': 100,
                        },
                        {
                            'artist_name': 'Tom Ellis',
                            'listen_count': 50,
                        }
                    ],
                    'count': 2,
                }
            ]
        }

        handle_user_entity(data)

        received = db_stats.get_user_stats(1, 'all_time', 'artists')
        expected = StatApi[EntityRecord](
            user_id=1,
            to_ts=10,
            from_ts=1,
            count=1,
            stats_range='all_time',
            data=StatRecordList[EntityRecord](
                __root__=[
                    ArtistRecord(
                        artist_mbids=[],
                        listen_count=200,
                        artist_name='Kanye West',
                    )
                ]
            ),
            last_updated=received.last_updated
        )
        self.assertEqual(received, expected)

        received = db_stats.get_user_stats(2, 'all_time', 'artists')
        expected = StatApi[EntityRecord](
            user_id=2,
            to_ts=10,
            from_ts=1,
            count=2,
            stats_range='all_time',
            data=StatRecordList[EntityRecord](
                __root__=[
                    ArtistRecord(
                        artist_mbids=[],
                        listen_count=100,
                        artist_name='Selena Gomez',
                    ),
                    ArtistRecord(
                        artist_mbids=[],
                        listen_count=50,
                        artist_name='Tom Ellis',
                    )
                ]
            ),
            last_updated=received.last_updated
        )
        self.assertEqual(received, expected)

    def test_handle_user_listening_activity(self):
        data = {
            'type': 'listening_activity',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'data': [
                {
                    'user_id': 1,
                    'data': [
                        {
                            'from_ts': 1,
                            'to_ts': 5,
                            'time_range': '2020',
                            'listen_count': 200,
                        },
                        {
                            'from_ts': 6,
                            'to_ts': 10,
                            'time_range': '2021',
                            'listen_count': 150,
                        },
                    ]
                },
                {
                    'user_id': 2,
                    'data': [
                        {
                            'from_ts': 2,
                            'to_ts': 7,
                            'time_range': '2020',
                            'listen_count': 20,
                        }
                    ]
                }
            ]
        }

        handle_user_listening_activity(data)

        received = db_stats.get_user_listening_activity(1, 'all_time')
        self.assertEqual(received, StatApi[ListeningActivityRecord](
            user_id=1,
            to_ts=10,
            from_ts=1,
            stats_range='all_time',
            data=StatRecordList[ListeningActivityRecord](
                __root__=[
                    ListeningActivityRecord(
                        from_ts=1,
                        to_ts=5,
                        time_range='2020',
                        listen_count=200,
                    ),
                    ListeningActivityRecord(
                        from_ts=6,
                        to_ts=10,
                        time_range='2021',
                        listen_count=150,
                    ),
                ]
            ),
            last_updated=received.last_updated
        ))

        received = db_stats.get_user_listening_activity(2, 'all_time')
        self.assertEqual(received, StatApi[ListeningActivityRecord](
            user_id=2,
            to_ts=10,
            from_ts=1,
            stats_range='all_time',
            data=StatRecordList[ListeningActivityRecord](
                __root__=[
                    ListeningActivityRecord(
                        from_ts=2,
                        to_ts=7,
                        time_range='2020',
                        listen_count=20,
                    )
                ]
            ),
            last_updated=received.last_updated
        ))

    def test_handle_user_daily_activity(self):
        data = {
            'type': 'daily_activity',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'data': [
                {
                    'user_id': 1,
                    'data': [
                        {
                            'day': 'Monday',
                            'hour': 20,
                            'listen_count': 20,
                        }
                    ]
                },
                {
                    'user_id': 2,
                    'data': [
                        {
                            'day': 'Wednesday',
                            'hour': 10,
                            'listen_count': 25,
                        },
                        {
                            'day': 'Friday',
                            'hour': 11,
                            'listen_count': 22,
                        }
                    ]
                }
            ],
        }

        handle_user_daily_activity(data)

        received = db_stats.get_user_daily_activity(1, 'all_time')
        self.assertEqual(received, StatApi[DailyActivityRecord](
            user_id=1,
            to_ts=10,
            from_ts=1,
            stats_range='all_time',
            data=StatRecordList[DailyActivityRecord](
                __root__=[
                    DailyActivityRecord(
                        day='Monday',
                        hour=20,
                        listen_count=20,
                    )
                ]
            ),
            last_updated=received.last_updated
        ))

        received = db_stats.get_user_daily_activity(2, 'all_time')
        self.assertEqual(received, StatApi[DailyActivityRecord](
            user_id=2,
            to_ts=10,
            from_ts=1,
            stats_range='all_time',
            data=StatRecordList[DailyActivityRecord](
                __root__=[
                    DailyActivityRecord(
                        day='Wednesday',
                        hour=10,
                        listen_count=25,
                    ),
                    DailyActivityRecord(
                        day='Friday',
                        hour=11,
                        listen_count=22,
                    ),
                ]
            ),
            last_updated=received.last_updated
        ))

    @mock.patch('listenbrainz.spark.handlers.db_stats.insert_sitewide_jsonb_data')
    @mock.patch('listenbrainz.spark.handlers.is_new_user_stats_batch')
    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_handle_user_daily_activity(self, mock_send_mail, mock_sitewide_stats, mock_db_insert):
        data = {
            'type': 'sitewide_entity',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'entity': 'artists',
            'data': [
                {
                    'artist_name': 'Coldplay',
                    'artist_mbid': [],
                    'listen_count': 20
                }
            ],
            'count': 1
        }

        with self.app.app_context():
            current_app.config['TESTING'] = False  # set testing to false to check the notifications
            handle_sitewide_entity(data)

        mock_db_insert.assert_called_with('artists', StatRange[ArtistRecord](
            to_ts=10,
            from_ts=1,
            count=1,
            stats_range='all_time',
            data=StatRecordList[ArtistRecord](__root__=[
                ArtistRecord(
                    artist_name='Coldplay',
                    artist_mbid=[],
                    listen_count=20,
                )
            ])))
        mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.db_stats.get_timestamp_for_last_user_stats_update')
    def test_is_new_user_stats_batch(self, mock_db_get_timestamp):
        mock_db_get_timestamp.return_value = datetime.now(timezone.utc)
        self.assertFalse(is_new_user_stats_batch())
        mock_db_get_timestamp.return_value = datetime.now(timezone.utc) - timedelta(minutes=21)
        self.assertTrue(is_new_user_stats_batch())

    @mock.patch('listenbrainz.spark.handlers.db_recommendations_cf_recording.insert_user_recommendation')
    @mock.patch('listenbrainz.spark.handlers.db_user.get')
    def test_handle_recommendations(self, mock_get, mock_db_insert):
        data = {
            'user_id': 1,
            'type': 'cf_recording_recommendations',
            'recommendations': {
                'top_artist': [
                    {
                        'recording_mbid': "2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                        'score': 1.8
                    },
                    {
                        'recording_mbid': "8acb406f-c716-45f8-a8bd-96ca3939c2e5",
                        'score': -0.8
                    }
                ],
                'similar_artist': []
            }
        }

        mock_get.return_value = {'id': 1, 'musicbrainz_id': 'vansika'}
        with self.app.app_context():
            handle_recommendations(data)

        mock_db_insert.assert_called_with(
            1,
            UserRecommendationsJson(
                top_artist=[
                    UserRecommendationsRecord(
                        recording_mbid="2acb406f-c716-45f8-a8bd-96ca3939c2e5",
                        score=1.8
                    ),
                    UserRecommendationsRecord(
                        recording_mbid="8acb406f-c716-45f8-a8bd-96ca3939c2e5",
                        score=-0.8
                    ),
                ],
                similar_artist=[]
            )
        )

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
            errors = ["Could not download dump!"]

            # testing, should not send a mail
            self.app.config['TESTING'] = True
            handle_dump_imported({
                'imported_dump': dump_name,
                'errors': errors,
                'type': 'import_full_dump',
                'time': str(time),
            })
            mock_send_mail.assert_not_called()

            # in prod now, should send it
            self.app.config['TESTING'] = False
            handle_dump_imported({
                'imported_dump': dump_name,
                'errors': errors,
                'type': 'import_full_dump',
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
            import_time = datetime.now()
            time_taken_to_import = 11
            mapping_name = 'msid-mbid-mapping-with-matchable-20200603-202731.tar.bz2'

            # testing, should not send a mail
            self.app.config['TESTING'] = True
            notify_mapping_import({
                'imported_mapping': mapping_name,
                'import_time': str(import_time),
                'time_taken_to_import': str(time_taken_to_import),
            })
            mock_send_mail.assert_not_called()

            # in prod now, should send it
            self.app.config['TESTING'] = False
            notify_mapping_import({
                'imported_mapping': mapping_name,
                'import_time': str(import_time),
                'time_taken_to_import': str(time_taken_to_import),
            })
            mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_notify_artist_relation_import(self, mock_send_mail):
        with self.app.app_context():
            import_time = datetime.now()
            time_taken_to_import = 11
            artist_relation_name = 'artist-credit-artist-credit-relations-01-20191230-134806.tar.bz2'

            # testing, should not send a mail
            self.app.config['TESTING'] = True
            notify_artist_relation_import({
                'imported_artist_relation': artist_relation_name,
                'import_time': str(import_time),
                'time_taken_to_import': str(time_taken_to_import),
            })
            mock_send_mail.assert_not_called()

            # in prod now, should send it
            self.app.config['TESTING'] = False
            notify_artist_relation_import({
                'imported_artist_relation': artist_relation_name,
                'import_time': str(import_time),
                'time_taken_to_import': str(time_taken_to_import),
            })
            mock_send_mail.assert_called_once()

    @mock.patch('listenbrainz.spark.handlers.db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data')
    @mock.patch('listenbrainz.spark.handlers.db_user.get')
    def test_handle_missing_musicbrainz_data(self, mock_get, mock_db_insert):
        data = {
            'type': 'missing_musicbrainz_data',
            'user_id': 1,
            'missing_musicbrainz_data': [
                {
                    "artist_name": "Katty Peri",
                    "listened_at": "2020-04-29 23:56:23",
                    "release_name": "No Place Is Home",
                    "recording_name": "How High"
                }
            ],
            'source': 'cf'
        }

        mock_get.return_value = {'id': 1, 'musicbrainz_id': 'vansika'}

        with self.app.app_context():
            handle_missing_musicbrainz_data(data)

        mock_db_insert.assert_called_with(
            1,
            UserMissingMusicBrainzDataJson(
                missing_musicbrainz_data=[UserMissingMusicBrainzDataRecord(
                    artist_name="Katty Peri",
                    listened_at="2020-04-29 23:56:23",
                    release_name="No Place Is Home",
                    recording_name="How High"
                )]),
            'cf'
        )
