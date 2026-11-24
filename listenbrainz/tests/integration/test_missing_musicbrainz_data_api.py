import datetime
import json
import orjson

import sqlalchemy

import listenbrainz.db.user as db_user
import listenbrainz.db.mbid_manual_mapping as db_mbid_manual_mapping
import listenbrainz.db.missing_musicbrainz_data as db_missing_musicbrainz_data
from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataJson
from listenbrainz.db import listens as listens_db
from listenbrainz.db.model.mbid_manual_mapping import MbidManualMapping
from listenbrainz.db.testing import TimescaleTestCase
from listenbrainz.tests.integration import IntegrationTestCase


class MissingMusicBrainzDataViewsTestCase(IntegrationTestCase):
    def setUp(self):
        IntegrationTestCase.setUp(self)

        self.user = db_user.get_or_create(self.db_conn, 1, 'vansika_1')
        self.user2 = db_user.get_or_create(self.db_conn, 2, 'vansika_2')

        with open(self.path_to_data_file('missing_musicbrainz_data.json'), 'r') as f:
            missing_musicbrainz_data = json.load(f)

        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            self.db_conn,
            user_id=self.user['id'],
            missing_musicbrainz_data=UserMissingMusicBrainzDataJson(missing_musicbrainz_data=missing_musicbrainz_data),
            source='cf'
        )
        self.listens_conn = listens_db.engine.connect()
        self.data = db_missing_musicbrainz_data.get_user_missing_musicbrainz_data(
            self.db_conn,
            self.listens_conn,
            user_id=self.user['id'],
            source='cf'
        )

    def tearDown(self):
        self.listens_conn.close()
        IntegrationTestCase.tearDown(self)

    def test_invalid_user(self):
        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name='invalid_user'))
        self.assert404(response)

    def test_user_musicbrainz_data_not_calculated(self):
        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user2['musicbrainz_id']))
        self.assertEqual(response.status_code, 204)

    def test_missing_musicbrainz_data_without_count(self):
        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 25)

        received_offset = data['offset']
        self.assertEqual(received_offset, 0)

        received_total_count = data['total_data_count']
        expected_total_count = len(self.data[0])
        self.assertEqual(received_total_count, expected_total_count)

        received_ts = data['last_updated']
        expected_ts = int(self.data[1].timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_data = data['data']
        expected_data = self.data[0][:25]
        self.assertEqual(expected_data, received_data)

    def test_missing_musicbrainz_data_with_count(self):
        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user['musicbrainz_id']),
                                   query_string={'count': 10})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 10)

        received_offset = data['offset']
        self.assertEqual(received_offset, 0)

        received_total_count = data['total_data_count']
        expected_total_count = len(self.data[0])
        self.assertEqual(received_total_count, expected_total_count)

        received_ts = data['last_updated']
        expected_ts = int(self.data[1].timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_data = data['data']
        expected_data = self.data[0][:10]
        self.assertEqual(expected_data, received_data)

    def test_missing_musicbrainz_data_too_many(self):
        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user['musicbrainz_id']),
                                   query_string={'count': 100})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 100)

        received_offset = data['offset']
        self.assertEqual(received_offset, 0)

        received_total_count = data['total_data_count']
        expected_total_count = len(self.data[0])
        self.assertEqual(received_total_count, expected_total_count)

        received_ts = data['last_updated']
        expected_ts = int(self.data[1].timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_data = data['data']
        expected_data = self.data[0][:100]
        self.assertEqual(expected_data, received_data)

    def test_missing_musicbrainz_data_with_offset(self):
        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user['musicbrainz_id']),
                                   query_string={'offset': 10})

        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 15)

        received_offset = data['offset']
        self.assertEqual(received_offset, 10)

        received_total_count = data['total_data_count']
        expected_total_count = len(self.data[0])
        self.assertEqual(received_total_count, expected_total_count)

        received_ts = data['last_updated']
        expected_ts = int(self.data[1].timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_data = data['data']
        expected_data = self.data[0][10:25]
        self.assertEqual(expected_data, received_data)


API_FULL_SERVICE_INFO = {
    "spotify_id": "https://open.spotify.com/track/2TZIQDtf2H4bazKfBa6I4T",
    "spotify_album_id": "https://open.spotify.com/album/2HaqZjwdtGVdDsoenjoJrT",
    "youtube_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "apple_music_id": "1440833692",
    "apple_album_id": "1440833683",
    "origin_url": "https://example.com/origin",
    "music_service": "spotify.com",
    "music_service_name": "Spotify",
}

API_INVALID_SERVICE_INFO = {
    "submission_client": "quodlibet",
    "custom_field": {"nested": True},
    "is_valid": True,
}


class MissingMusicBrainzDataServiceMetadataAPITestCase(IntegrationTestCase, TimescaleTestCase):
    """ Tests for service metadata hydrated into the public missing MusicBrainz data API. """

    def setUp(self):
        IntegrationTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.user = db_user.get_or_create(self.db_conn, 1, 'vansika_meta')

    def tearDown(self):
        TimescaleTestCase.tearDown(self)
        IntegrationTestCase.tearDown(self)

    def _insert_cache(self, records):
        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            self.db_conn,
            user_id=self.user['id'],
            missing_musicbrainz_data=UserMissingMusicBrainzDataJson(missing_musicbrainz_data=records),
            source='cf',
        )

    def _cache_created(self):
        result = self.db_conn.execute(sqlalchemy.text("""
            SELECT created
              FROM missing_musicbrainz_data
             WHERE user_id = :user_id
               AND source = 'cf'
            """), {'user_id': self.user['id']})
        return result.scalar_one()

    def test_service_metadata_in_response(self):
        """ A record hydrated from its stored listen exposes only allowlisted metadata. """
        msid = "abababab-abab-4aba-8aba-abababababab"
        record = {
            "artist_name": "Api Artist",
            "listened_at": "2026-11-04T10:00:00.000Z",
            "release_name": "Api Release",
            "recording_name": "Api Track",
            "recording_msid": msid,
        }
        self._insert_cache([record])
        track_metadata = {
            "artist_name": "Api Artist",
            "track_name": "Api Track",
            "release_name": "Api Release",
            "additional_info": {**API_FULL_SERVICE_INFO, **API_INVALID_SERVICE_INFO},
        }
        listens_db.insert([(
            datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc),
            self.user['id'],
            msid,
            orjson.dumps(track_metadata).decode("utf-8"),
        )])
        created = self._cache_created()

        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user['musicbrainz_id']))

        self.assert200(response)
        payload = json.loads(response.data)['payload']
        self.assertEqual(1, payload['count'])
        self.assertEqual(1, payload['total_data_count'])
        self.assertEqual(0, payload['offset'])
        self.assertEqual(int(created.timestamp()), payload['last_updated'])
        self.assertEqual([dict(record, additional_info=dict(API_FULL_SERVICE_INFO))], payload['data'])

    def test_legacy_records_unchanged_in_response(self):
        """ A record without a stored representative listen keeps its exact legacy shape. """
        record = {
            "artist_name": "Legacy Artist",
            "listened_at": "2026-11-04T10:00:00.000Z",
            "release_name": None,
            "recording_name": "Legacy Track",
            "recording_msid": "bcbcbcbc-bcbc-4bcb-8bcb-bcbcbcbcbcbc",
        }
        self._insert_cache([record])
        created = self._cache_created()

        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user['musicbrainz_id']))

        self.assert200(response)
        payload = json.loads(response.data)['payload']
        self.assertEqual(int(created.timestamp()), payload['last_updated'])
        self.assertEqual([record], payload['data'])
        self.assertNotIn('additional_info', payload['data'][0])

    def test_paginated_metadata_preserves_order_and_filtered_total(self):
        """ Pagination preserves enriched and legacy records after removing manual mappings. """
        base = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        records = []
        expected = []
        listens = []
        for i in range(6):
            msid = f"00000000-0000-4000-8000-{i + 1:012d}"
            listened_at = base + datetime.timedelta(seconds=i)
            record = {
                "artist_name": "Page Artist",
                "listened_at": listened_at.isoformat(timespec="milliseconds"),
                "release_name": None,
                "recording_name": f"Page Track {i}",
                "recording_msid": msid,
            }
            records.append(record)
            expected_record = dict(record)
            if i % 2 == 0:
                metadata = {"music_service_name": f"Service {i}"}
                expected_record["additional_info"] = metadata
                listens.append((listened_at, listened_at, self.user['id'], msid,
                                orjson.dumps({"artist_name": record["artist_name"],
                                              "track_name": record["recording_name"],
                                              "additional_info": metadata}).decode("utf-8")))
            if i != 0:
                expected.append(expected_record)
        self._insert_cache(records)
        listens_db.insert(listens)
        db_mbid_manual_mapping.create_mbid_manual_mapping(
            self.listens_conn,
            MbidManualMapping(recording_msid=records[0]["recording_msid"],
                              recording_mbid="c8d63620-ced3-4abf-84f8-85457ce798c6", user_id=self.user['id']),
        )
        created = self._cache_created()

        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user['musicbrainz_id']),
                                   query_string={"offset": 1, "count": 4})

        self.assert200(response)
        payload = json.loads(response.data)['payload']
        self.assertEqual(expected[1:4], payload['data'])
        self.assertEqual(3, payload['count'])
        self.assertEqual(5, payload['total_data_count'])
        self.assertEqual(1, payload['offset'])
        self.assertEqual(int(created.timestamp()), payload['last_updated'])
        self.assertEqual(created, self._cache_created())

    def test_malformed_cache_returns_no_content(self):
        """ A cache row that fails validation yields no data instead of an error. """
        self.db_conn.execute(sqlalchemy.text("""
            INSERT INTO missing_musicbrainz_data (user_id, data, source)
                 VALUES (:user_id, :data, 'cf')
            """), {
                'user_id': self.user['id'],
                'data': orjson.dumps({"missing_musicbrainz_data": {"unexpected": "shape"}}).decode("utf-8"),
            })
        self.db_conn.commit()

        response = self.client.get(self.custom_url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                                       user_name=self.user['musicbrainz_id']))

        self.assertEqual(response.status_code, 204)
