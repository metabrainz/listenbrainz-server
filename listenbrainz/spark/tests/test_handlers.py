from datetime import datetime
from unittest import mock
from unittest.mock import call

from data.model.common_stat import StatRecordList, StatApi
from data.model.user_artist_stat import ArtistRecord
from data.model.user_cf_recommendations_recording_message import (UserRecommendationsJson,
                                                                  UserRecommendationsRecord)
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from data.model.user_missing_musicbrainz_data import (UserMissingMusicBrainzDataRecord,
                                                      UserMissingMusicBrainzDataJson)
from listenbrainz.db import stats as db_stats
from listenbrainz.db import user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db.tests.utils import delete_all_couch_databases
from listenbrainz.spark.handlers import (
    handle_candidate_sets, handle_dataframes, handle_dump_imported,
    handle_model, handle_recommendations, handle_sitewide_entity,
    handle_user_daily_activity, handle_user_entity,
    handle_user_listening_activity,
    notify_mapping_import,
    handle_missing_musicbrainz_data,
    cf_recording_recommendations_complete)
from listenbrainz.spark.spark_dataset import CouchDbDataset
from listenbrainz.webserver import create_app


class HandlersTestCase(DatabaseTestCase):

    def setUp(self):
        super(HandlersTestCase, self).setUp()
        self.app = create_app()
        self.user1 = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        self.user2 = db_user.get_or_create(self.db_conn, 2, 'lucifer')

    def tearDown(self):
        super(HandlersTestCase, self).tearDown()
        delete_all_couch_databases()

    def test_handle_user_entity(self):
        data = {
            'type': 'user_entity',
            'entity': 'artists',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'data': [
                {
                    'user_id': self.user1['id'],
                    'data': [{
                        'artist_name': 'Kanye West',
                        'listen_count': 200,
                    }],
                    'count': 1,
                },
                {
                    'user_id': self.user2['id'],
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
            ],
            'database': 'artists_all_time_20220718'
        }
        CouchDbDataset.handle_start({"database": "artists_all_time_20220718"})
        handle_user_entity(data)

        received = db_stats.get(self.user1['id'], 'artists', 'all_time', EntityRecord)
        expected = StatApi[EntityRecord](
            user_id=self.user1['id'],
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

        received = db_stats.get(self.user2['id'], 'artists', 'all_time', EntityRecord)
        expected = StatApi[EntityRecord](
            user_id=self.user2['id'],
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
                    'user_id': self.user1['id'],
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
                    'user_id': self.user2['id'],
                    'data': [
                        {
                            'from_ts': 2,
                            'to_ts': 7,
                            'time_range': '2020',
                            'listen_count': 20,
                        }
                    ]
                }
            ],
            'database': 'listening_activity_all_time_20220718'
        }
        CouchDbDataset.handle_start({"database": "listening_activity_all_time_20220718"})
        handle_user_listening_activity(data)

        received = db_stats.get(self.user1['id'], 'listening_activity', 'all_time', ListeningActivityRecord)
        self.assertEqual(received, StatApi[ListeningActivityRecord](
            user_id=self.user1['id'],
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

        received = db_stats.get(self.user2['id'], 'listening_activity', 'all_time', ListeningActivityRecord)
        self.assertEqual(received, StatApi[ListeningActivityRecord](
            user_id=self.user2['id'],
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
                    'user_id': self.user1['id'],
                    'data': [
                        {
                            'day': 'Monday',
                            'hour': 20,
                            'listen_count': 20,
                        }
                    ]
                },
                {
                    'user_id': self.user2['id'],
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
            'database': 'daily_activity_all_time_20220718'
        }
        CouchDbDataset.handle_start({"database": "daily_activity_all_time_20220718"})
        handle_user_daily_activity(data)

        received = db_stats.get(self.user1['id'], 'daily_activity', 'all_time', DailyActivityRecord)
        self.assertEqual(received, StatApi[DailyActivityRecord](
            user_id=self.user1['id'],
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

        received = db_stats.get(self.user2['id'], 'daily_activity', 'all_time', DailyActivityRecord)
        self.assertEqual(received, StatApi[DailyActivityRecord](
            user_id=self.user2['id'],
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

    def test_handle_sitewide_artists(self):
        data = {
            'type': 'sitewide_entity',
            'stats_range': 'all_time',
            'from_ts': 1,
            'to_ts': 10,
            'entity': 'artists',
            'data': [
                {
                    'artist_name': 'Coldplay',
                    'artist_mbid': None,
                    'listen_count': 20
                }
            ],
            'count': 1
        }
        CouchDbDataset.handle_start({"database": "artists_all_time_20220818"})
        handle_sitewide_entity(data)
        stats = db_stats.get_sitewide_stats("artists","all_time")
        self.assertEqual(stats["count"], data["count"])
        self.assertEqual(stats["from_ts"], data["from_ts"])
        self.assertEqual(stats["to_ts"], data["to_ts"])
        self.assertEqual(stats["data"], data["data"])


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
            mock.ANY,
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

    @mock.patch('listenbrainz.troi.daily_jams.get_followers_of_user')
    @mock.patch('listenbrainz.troi.daily_jams.RecommendationsToPlaylistPatch')
    @mock.patch('listenbrainz.spark.handlers.send_mail')
    def test_cf_recording_recommendations_complete(self, mock_send_mail, mock_recs_patch, mock_get_followers):
        with self.app.app_context():
            active_user_count = 10
            top_artist_user_count = 5
            similar_artist_user_count = 4
            total_time = datetime.now()

            # testing, should not send a mail
            self.app.config['TESTING'] = True
            self.app.config["WHITELISTED_AUTH_TOKENS"] = ["fake_token0", "fake_token1"]

            mock_recs_patch.generate_playlist.return_value = "https://listenbrainz.org/playlist/97889d4d-1474-4a9b-925a-851148356f9d/"
            mock_get_followers.return_value = [{"musicbrainz_id": "lucifer"}]

            cf_recording_recommendations_complete({
                'active_user_count': active_user_count,
                'top_artist_user_count': top_artist_user_count,
                'similar_artist_user_count': similar_artist_user_count,
                'total_time': str(total_time)
            })
            mock_send_mail.assert_not_called()

            calls = [
                call({'user_name': 'lucifer', 'upload': True, 'token': 'fake_token1', 'created_for': 'lucifer', 'echo': False, 'type': 'top'}),
                call({'user_name': 'lucifer', 'upload': True, 'token': 'fake_token1', 'created_for': 'lucifer', 'echo': False, 'type': 'similar'}),
            ]
            mock_recs_patch.assert_has_calls(calls, any_order=True)

            # in prod now, should send it
            self.app.config['TESTING'] = False
            cf_recording_recommendations_complete({
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
            dump_name = 'listenbrainz-listens-dump-20200223-000000-spark-full.tar.zst'
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
                    "recording_name": "How High",
                    "recording_msid": "aab9ec01-89ac-4026-a1c7-4cf6e347aec8"
                }
            ],
            'source': 'cf'
        }

        mock_get.return_value = {'id': 1, 'musicbrainz_id': 'vansika'}

        with self.app.app_context():
            handle_missing_musicbrainz_data(data)

        mock_db_insert.assert_called_with(
            mock.ANY,
            1,
            UserMissingMusicBrainzDataJson(
                missing_musicbrainz_data=[UserMissingMusicBrainzDataRecord(
                    artist_name="Katty Peri",
                    listened_at="2020-04-29 23:56:23",
                    release_name="No Place Is Home",
                    recording_name="How High",
                    recording_msid="aab9ec01-89ac-4026-a1c7-4cf6e347aec8"
                )]),
            'cf'
        )
