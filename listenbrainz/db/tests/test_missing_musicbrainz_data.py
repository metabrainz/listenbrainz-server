import datetime
import json
import orjson
import uuid

import sqlalchemy

import listenbrainz.db.mbid_manual_mapping as db_mbid_manual_mapping
import listenbrainz.db.missing_musicbrainz_data as db_missing_musicbrainz_data
import listenbrainz.db.user as db_user

from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataJson
from listenbrainz.db import listens as listens_db
from listenbrainz.db.model.mbid_manual_mapping import MbidManualMapping
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase


FULL_SERVICE_INFO = {
    "spotify_id": "https://open.spotify.com/track/2TZIQDtf2H4bazKfBa6I4T",
    "spotify_album_id": "https://open.spotify.com/album/2HaqZjwdtGVdDsoenjoJrT",
    "youtube_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "apple_music_id": "1440833692",
    "apple_album_id": "1440833683",
    "origin_url": "https://example.com/origin",
    "music_service": "spotify.com",
    "music_service_name": "Spotify",
}

INVALID_SERVICE_INFO = {
    "spotify_id": 123,
    "origin_url": None,
    "youtube_id": "   ",
    "music_service": ["spotify.com"],
    "submission_client": "quodlibet",
    "custom_field": {"nested": True},
    "is_valid": True,
}

UNKNOWN_SERVICE_INFO = {
    "submission_client": "quodlibet",
    "custom_field": {"nested": True},
    "is_valid": True,
}


def _cache_record(artist_name, recording_name, recording_msid, listened_at, release_name=None):
    """ Build a cached missing-data record with the fields the spark job stores. """
    return {
        "artist_name": artist_name,
        "listened_at": listened_at,
        "release_name": release_name,
        "recording_name": recording_name,
        "recording_msid": recording_msid,
    }


def _stored_listen(user_id, listened_at, recording_msid, artist_name, track_name,
                   release_name=None, additional_info=None):
    """ Build a listens_db.insert row with the flat track_metadata the listens database stores. """
    track_metadata = {"artist_name": artist_name, "track_name": track_name}
    if release_name is not None:
        track_metadata["release_name"] = release_name
    if additional_info is not None:
        track_metadata["additional_info"] = additional_info
    return (listened_at, listened_at, user_id, recording_msid, orjson.dumps(track_metadata).decode("utf-8"))


class MissingMusicbrainzDataDatabaseTestCase(DatabaseTestCase, TimescaleTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.user = db_user.get_or_create(self.db_conn, 1, 'vansika')

    def tearDown(self):
        TimescaleTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def insert_test_data(self):
        """ Insert test data into the database """
        with open(self.path_to_data_file('missing_musicbrainz_data.json')) as f:
            missing_musicbrainz_data = json.load(f)

        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            self.db_conn,
            user_id=self.user['id'],
            missing_musicbrainz_data=UserMissingMusicBrainzDataJson(**{'missing_musicbrainz_data': missing_musicbrainz_data}),
            source='cf'
        )
        return missing_musicbrainz_data

    def test_insert_user_missing_musicbrainz_data(self):
        """ Test if user missing musicbrainz data is inserted correctly """
        with open(self.path_to_data_file('missing_musicbrainz_data.json')) as f:
            missing_musicbrainz_data = json.load(f)

        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            self.db_conn,
            user_id=self.user['id'],
            missing_musicbrainz_data=UserMissingMusicBrainzDataJson(**{'missing_musicbrainz_data': missing_musicbrainz_data}),
            source='cf'
        )

        result = db_missing_musicbrainz_data.get_user_missing_musicbrainz_data(
            self.db_conn, self.listens_conn, user_id=self.user['id'], source='cf'
        )
        self.assertEqual(missing_musicbrainz_data, result[0])

    def test_get_user_missing_musicbrainz_data(self):
        data_inserted = self.insert_test_data()
        result = db_missing_musicbrainz_data.get_user_missing_musicbrainz_data(
            self.db_conn, self.listens_conn, user_id=self.user['id'], source='cf'
        )
        self.assertEqual(data_inserted, result[0])

    def test_multiple_inserts_into_db(self):
        """ Test if data associated with a user id is updated on multiple inserts.
        """
        with open(self.path_to_data_file('missing_musicbrainz_data.json')) as f:
            missing_musicbrainz_data = json.load(f)

        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            self.db_conn,
            user_id=self.user['id'],
            missing_musicbrainz_data=UserMissingMusicBrainzDataJson(**{'missing_musicbrainz_data': missing_musicbrainz_data}),
            source='cf'
        )

        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            self.db_conn,
            user_id=self.user['id'],
            missing_musicbrainz_data=UserMissingMusicBrainzDataJson(**{'invalid_key': missing_musicbrainz_data}),
            source='cf'
        )

        result = db_missing_musicbrainz_data.get_user_missing_musicbrainz_data(
            self.db_conn, self.listens_conn, user_id=self.user['id'], source='cf'
        )
        self.assertIsNone(result[0])
        self.assertIsNotNone(result[1])


class MissingMusicbrainzDataServiceMetadataTestCase(DatabaseTestCase, TimescaleTestCase):
    """ Tests for attaching submitted service metadata from the listens database
        to cached missing MusicBrainz data records.
    """

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.user = db_user.get_or_create(self.db_conn, 1, 'vansika_meta')
        self.other_user = db_user.get_or_create(self.db_conn, 2, 'other_meta_user')

    def tearDown(self):
        TimescaleTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def _insert_cache(self, records):
        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            self.db_conn,
            user_id=self.user['id'],
            missing_musicbrainz_data=UserMissingMusicBrainzDataJson(missing_musicbrainz_data=records),
            source='cf',
        )

    def _get_missing_data(self):
        return db_missing_musicbrainz_data.get_user_missing_musicbrainz_data(
            self.db_conn, self.listens_conn, user_id=self.user['id'], source='cf'
        )

    def _raw_cache_row(self):
        result = self.db_conn.execute(sqlalchemy.text("""
            SELECT data, created
              FROM missing_musicbrainz_data
             WHERE user_id = :user_id
               AND source = 'cf'
            """), {'user_id': self.user['id']})
        return result.mappings().first()

    def test_exact_match_attaches_allowlisted_service_metadata(self):
        """ A stored listen matching the record's identity supplies only allowlisted fields. """
        msid = "11111111-1111-4111-8111-111111111111"
        record = _cache_record("Meta Artist", "Meta Track", msid, "2026-11-04T10:00:00.000Z",
                               release_name="Meta Release")
        self._insert_cache([record])
        listens_db.insert([
            _stored_listen(self.user['id'], datetime.datetime(2026, 11, 4, 10, 0, 0,
                                                              tzinfo=datetime.timezone.utc),
                           msid, "Meta Artist", "Meta Track", release_name="Meta Release",
                           additional_info={**FULL_SERVICE_INFO, **UNKNOWN_SERVICE_INFO}),
        ])

        data, created = self._get_missing_data()

        self.assertIsNotNone(created)
        expected = dict(record, additional_info=dict(FULL_SERVICE_INFO))
        self.assertEqual([expected], data)

    def test_invalid_service_metadata_values_are_omitted(self):
        """ Blank, null, non-string and unknown values are dropped; absent or non-object
            additional_info leaves the record without the field.
        """
        msid_valid = "22222222-2222-4222-8222-222222222222"
        msid_empty = "33333333-3333-4333-8333-333333333333"
        msid_absent = "44444444-4444-4444-8444-444444444444"
        ts = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        iso_ts = "2026-11-04T10:00:00.000Z"
        records = [
            _cache_record("Filter Artist", "Filter Track", msid_valid, iso_ts),
            _cache_record("Empty Artist", "Empty Track", msid_empty, iso_ts),
            _cache_record("Absent Artist", "Absent Track", msid_absent, iso_ts),
        ]
        self._insert_cache(records)
        listens_db.insert([
            _stored_listen(self.user['id'], ts, msid_valid, "Filter Artist", "Filter Track",
                           additional_info={"music_service_name": "Bandcamp", **INVALID_SERVICE_INFO}),
            _stored_listen(self.user['id'], ts, msid_empty, "Empty Artist", "Empty Track",
                           additional_info={}),
            _stored_listen(self.user['id'], ts, msid_absent, "Absent Artist", "Absent Track",
                           additional_info="not an object"),
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([dict(records[0], additional_info={"music_service_name": "Bandcamp"}),
                          records[1],
                          records[2]], data)

    def test_no_matching_listen_returns_legacy_record(self):
        """ A record without a stored representative listen is returned unchanged. """
        record = _cache_record("Ghost Artist", "Ghost Track", "55555555-5555-4555-8555-555555555555",
                               "2026-11-04T10:00:00.000Z", release_name="Ghost Release")
        self._insert_cache([record])

        data, created = self._get_missing_data()

        self.assertIsNotNone(created)
        self.assertEqual([record], data)

    def test_same_msid_at_other_timestamps_is_not_used(self):
        """ Listens of the same recording at unrelated times cannot supply metadata. """
        msid = "66666666-6666-4666-8666-666666666666"
        record = _cache_record("Time Artist", "Time Track", msid, "2026-11-04T10:00:00.000Z")
        self._insert_cache([record])
        base = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        listens_db.insert([
            _stored_listen(self.user['id'], base + datetime.timedelta(hours=1), msid,
                           "Time Artist", "Time Track", additional_info=FULL_SERVICE_INFO),
            _stored_listen(self.user['id'], base - datetime.timedelta(hours=1), msid,
                           "Time Artist", "Time Track", additional_info=FULL_SERVICE_INFO),
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([record], data)

    def test_same_msid_release_groups_hydrate_independently(self):
        """ Records sharing an msid in different release groups each get their own metadata. """
        msid = "77777777-7777-4777-8777-777777777777"
        record_one = _cache_record("Group Artist", "Group Track", msid, "2026-11-04T10:00:00.000Z",
                                   release_name="Release One")
        record_two = _cache_record("Group Artist", "Group Track", msid, "2026-11-04T10:01:00.000Z",
                                   release_name="Release Two")
        self._insert_cache([record_one, record_two])
        base = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        listens_db.insert([
            _stored_listen(self.user['id'], base, msid, "Group Artist", "Group Track",
                           release_name="Release One",
                           additional_info={"spotify_album_id": FULL_SERVICE_INFO["spotify_album_id"]}),
            _stored_listen(self.user['id'], base + datetime.timedelta(minutes=1), msid,
                           "Group Artist", "Group Track", release_name="Release Two",
                           additional_info={"origin_url": "https://example.com/release-two"}),
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([
            dict(record_one, additional_info={"spotify_album_id": FULL_SERVICE_INFO["spotify_album_id"]}),
            dict(record_two, additional_info={"origin_url": "https://example.com/release-two"}),
        ], data)

    def test_exact_timestamp_matching_variants(self):
        """ Exact matches attach metadata for second, millisecond and equivalent-offset
            cache timestamps.
        """
        base = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        cases = [
            ("88888888-8888-4888-8888-888888888888", "2026-11-04T10:00:00.000Z", base),
            ("99999999-9999-4999-8999-999999999999", "2026-11-04T15:30:00.000+05:30", base),
            ("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "2026-11-04T10:00:00.123Z",
             base + datetime.timedelta(milliseconds=123)),
        ]
        records = [
            _cache_record(f"Exact Artist {i}", f"Exact Track {i}", msid, listened_at)
            for i, (msid, listened_at, _) in enumerate(cases)
        ]
        self._insert_cache(records)
        listens_db.insert([
            _stored_listen(self.user['id'], stored_ts, msid, f"Exact Artist {i}", f"Exact Track {i}",
                           additional_info={"music_service": "spotify.com"})
            for i, (msid, _, stored_ts) in enumerate(cases)
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([dict(record, additional_info={"music_service": "spotify.com"})
                          for record in records], data)

    def test_millisecond_tolerance_policy(self):
        """ Within one cached millisecond, only an unambiguous names-matching candidate
            is accepted; exact matches always win and ambiguous candidates are withheld.
        """
        base = datetime.datetime(2026, 11, 4, 11, 0, 0, tzinfo=datetime.timezone.utc)
        msid_unique = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        msid_preferred = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
        msid_ambiguous = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
        msid_sub_ms = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
        msid_sub_ms_none = "ffffffff-ffff-4fff-8fff-ffffffffffff"
        msid_upper = "1a1a1a1a-1a1a-41a1-81a1-1a1a1a1a1a1a"
        records = [
            _cache_record("Tolerance Artist", "Tolerance Track", msid_unique, "2026-11-04T11:00:00.000Z"),
            _cache_record("Tolerance Artist", "Tolerance Track", msid_preferred, "2026-11-04T11:00:00.000Z"),
            _cache_record("Tolerance Artist", "Tolerance Track", msid_ambiguous, "2026-11-04T11:00:00.000Z"),
            _cache_record("Tolerance Artist", "Tolerance Track", msid_sub_ms, "2026-11-04T11:00:00.123456Z"),
            _cache_record("Tolerance Artist", "Tolerance Track", msid_sub_ms_none, "2026-11-04T11:00:00.123456Z"),
            _cache_record("Tolerance Artist", "Tolerance Track", msid_upper, "2026-11-04T11:00:00.000Z"),
        ]
        self._insert_cache(records)
        listens_db.insert([
            _stored_listen(self.user['id'], base + datetime.timedelta(microseconds=400), msid_unique,
                           "Tolerance Artist", "Tolerance Track",
                           additional_info={"music_service_name": "Unique"}),
            _stored_listen(self.user['id'], base + datetime.timedelta(microseconds=500), msid_preferred,
                           "Tolerance Artist", "Tolerance Track",
                           additional_info={"music_service_name": "Wrong"}),
            _stored_listen(self.user['id'], base, msid_preferred,
                           "Tolerance Artist", "Tolerance Track",
                           additional_info={"music_service_name": "Exact"}),
            _stored_listen(self.user['id'], base + datetime.timedelta(microseconds=300), msid_ambiguous,
                           "Tolerance Artist", "Tolerance Track",
                           additional_info={"music_service_name": "First"}),
            _stored_listen(self.user['id'], base + datetime.timedelta(microseconds=700), msid_ambiguous,
                           "Tolerance Artist", "Tolerance Track",
                           additional_info={"music_service_name": "Second"}),
            _stored_listen(self.user['id'], base + datetime.timedelta(microseconds=123456), msid_sub_ms,
                           "Tolerance Artist", "Tolerance Track",
                           additional_info={"music_service_name": "SubMsExact"}),
            _stored_listen(self.user['id'], base + datetime.timedelta(microseconds=123789), msid_sub_ms_none,
                           "Tolerance Artist", "Tolerance Track",
                           additional_info={"music_service_name": "SubMsWrong"}),
            _stored_listen(self.user['id'], base + datetime.timedelta(milliseconds=1), msid_upper,
                           "Tolerance Artist", "Tolerance Track",
                           additional_info={"music_service_name": "UpperBound"}),
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([
            dict(records[0], additional_info={"music_service_name": "Unique"}),
            dict(records[1], additional_info={"music_service_name": "Exact"}),
            records[2],
            dict(records[3], additional_info={"music_service_name": "SubMsExact"}),
            records[4],
            records[5],
        ], data)

    def test_name_mismatch_withholds_metadata(self):
        """ Candidates with different names never supply metadata; absent and null
            releases are equivalent, an empty release is not.
        """
        base = datetime.datetime(2026, 11, 4, 12, 0, 0, tzinfo=datetime.timezone.utc)
        msid_track = "2b2b2b2b-2b2b-42b2-82b2-2b2b2b2b2b2b"
        msid_release_null = "3c3c3c3c-3c3c-43c3-83c3-3c3c3c3c3c3c"
        msid_release_empty = "4d4d4d4d-4d4d-44d4-84d4-4d4d4d4d4d4d"
        records = [
            _cache_record("Name Artist", "Name Track", msid_track, "2026-11-04T12:00:00.000Z"),
            _cache_record("Name Artist", "Name Track", msid_release_null, "2026-11-04T12:00:00.000Z"),
            _cache_record("Name Artist", "Name Track", msid_release_empty, "2026-11-04T12:00:00.000Z"),
        ]
        self._insert_cache(records)
        listens_db.insert([
            _stored_listen(self.user['id'], base, msid_track, "Name Artist", "Different Track",
                           additional_info={"music_service": "spotify.com"}),
            _stored_listen(self.user['id'], base, msid_release_null, "Name Artist", "Name Track",
                           release_name=None, additional_info={"music_service": "spotify.com"}),
            _stored_listen(self.user['id'], base, msid_release_empty, "Name Artist", "Name Track",
                           release_name="", additional_info={"music_service": "spotify.com"}),
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([records[0],
                          dict(records[1], additional_info={"music_service": "spotify.com"}),
                          records[2]], data)

    def test_other_user_listen_cannot_supply_metadata(self):
        """ A listen of another user at the same instant and msid is not visible. """
        msid = "5e5e5e5e-5e5e-45e5-85e5-5e5e5e5e5e5e"
        record = _cache_record("Isolated Artist", "Isolated Track", msid, "2026-11-04T10:00:00.000Z")
        self._insert_cache([record])
        listens_db.insert([
            _stored_listen(self.other_user['id'], datetime.datetime(2026, 11, 4, 10, 0, 0,
                                                                    tzinfo=datetime.timezone.utc),
                           msid, "Isolated Artist", "Isolated Track", additional_info=FULL_SERVICE_INFO),
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([record], data)

    def test_manual_mapping_and_invalid_msid_handling(self):
        """ Manually mapped records are removed, a malformed msid does not poison the
            mapping lookup or the enrichment of other records.
        """
        base = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        msid_mapped = "6f6f6f6f-6f6f-46f6-86f6-6f6f6f6f6f6f"
        msid_valid = "7a7a7a7a-7a7a-47a7-87a7-7a7a7a7a7a7a"
        record_mapped = _cache_record("Mapped Artist", "Mapped Track", msid_mapped,
                                      "2026-11-04T10:00:00.000Z")
        record_valid = _cache_record("Valid Artist", "Valid Track", msid_valid,
                                     "2026-11-04T10:00:00.000Z")
        record_invalid = _cache_record("Invalid Artist", "Invalid Track", "not-a-uuid",
                                       "2026-11-04T10:00:00.000Z")
        self._insert_cache([record_mapped, record_valid, record_invalid])
        listens_db.insert([
            _stored_listen(self.user['id'], base, msid_mapped, "Mapped Artist", "Mapped Track",
                           additional_info={"music_service": "spotify.com"}),
            _stored_listen(self.user['id'], base, msid_valid, "Valid Artist", "Valid Track",
                           additional_info={"music_service": "spotify.com"}),
        ])
        db_mbid_manual_mapping.create_mbid_manual_mapping(
            self.listens_conn,
            MbidManualMapping(recording_msid=msid_mapped,
                              recording_mbid="c8d63620-ced3-4abf-84f8-85457ce798c6",
                              user_id=self.user['id']),
        )

        data, _ = self._get_missing_data()

        self.assertEqual([
            dict(record_valid, additional_info={"music_service": "spotify.com"}),
            record_invalid,
        ], data)

    def test_invalid_timestamp_suppresses_hydration_for_that_row(self):
        """ An unparseable cached timestamp only suppresses enrichment of its own record. """
        msid_valid = "8b8b8b8b-8b8b-48b8-88b8-8b8b8b8b8b8b"
        msid_naive = "9c9c9c9c-9c9c-49c9-89c9-9c9c9c9c9c9c"
        record_valid = _cache_record("Ts Artist", "Ts Track", msid_valid, "2026-11-04T10:00:00.000Z")
        record_bad = _cache_record("Ts Artist", "Ts Track", msid_naive, "not-a-timestamp")
        record_naive = _cache_record("Ts Artist", "Ts Track", "0d0d0d0d-0d0d-40d0-80d0-0d0d0d0d0d0d",
                                     "2026-11-04T10:00:00")
        self._insert_cache([record_valid, record_bad, record_naive])
        listens_db.insert([
            _stored_listen(self.user['id'], datetime.datetime(2026, 11, 4, 10, 0, 0,
                                                              tzinfo=datetime.timezone.utc),
                           msid_valid, "Ts Artist", "Ts Track",
                           additional_info={"music_service": "spotify.com"}),
            _stored_listen(self.user['id'], datetime.datetime(2026, 11, 4, 10, 0, 0,
                                                              tzinfo=datetime.timezone.utc),
                           msid_naive, "Ts Artist", "Ts Track",
                           additional_info={"music_service": "spotify.com"}),
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([
            dict(record_valid, additional_info={"music_service": "spotify.com"}),
            record_bad,
            record_naive,
        ], data)

    def test_overflowing_cached_timestamps_leave_other_rows_enriched(self):
        """ Timestamp arithmetic overflow only suppresses enrichment of the affected row. """
        base = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        msid = "a5a5a5a5-a5a5-45a5-85a5-a5a5a5a5a5a5"
        valid_record = _cache_record("Boundary Artist", "Boundary Track", msid, "2026-11-04T10:00:00.000Z")
        listens_db.insert([
            _stored_listen(self.user['id'], base, msid, "Boundary Artist", "Boundary Track",
                           additional_info={"music_service_name": "Spotify"}),
        ])

        for timestamp in ("0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59.999+00:00"):
            with self.subTest(timestamp=timestamp):
                boundary_record = _cache_record("Boundary Artist", "Boundary Track", msid, timestamp)
                self._insert_cache([boundary_record, valid_record])

                data, _ = self._get_missing_data()

                self.assertEqual([
                    boundary_record,
                    dict(valid_record, additional_info={"music_service_name": "Spotify"}),
                ], data)

    def test_exact_match_at_datetime_boundary_is_enriched(self):
        """ An exact match does not need a representable tolerance window. """
        msid = "b5b5b5b5-b5b5-45b5-85b5-b5b5b5b5b5b5"
        record = _cache_record("Boundary Artist", "Boundary Track", msid, "9999-12-31T23:59:59.999+00:00")
        self._insert_cache([record])
        listens_db.insert([
            _stored_listen(self.user['id'], datetime.datetime(9999, 12, 31, 23, 59, 59, 999000,
                                                              tzinfo=datetime.timezone.utc),
                           msid, "Boundary Artist", "Boundary Track",
                           additional_info={"music_service_name": "Spotify"}),
        ])

        data, _ = self._get_missing_data()

        self.assertEqual([dict(record, additional_info={"music_service_name": "Spotify"})], data)

    def test_tolerance_lookups_across_chunks_preserve_rows(self):
        """ Hits, misses, name mismatches and duplicate rows survive tolerance chunk boundaries. """
        base = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        records = []
        expected = []
        listens = []
        for i in range(17):
            msid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"lb-1053-tolerance-chunk-{i}"))
            listened_at = base + datetime.timedelta(seconds=i)
            record = _cache_record(f"Tolerance Artist {i}", f"Tolerance Track {i}", msid,
                                   listened_at.isoformat(timespec="milliseconds"))
            records.append(record)
            metadata = {"music_service_name": f"Service {i}"}
            expected_record = dict(record, additional_info=metadata) if i % 3 == 0 else dict(record)
            expected.append(expected_record)
            if i % 3 != 1:
                track_name = record["recording_name"] if i % 3 == 0 else "Different Track"
                listens.append(_stored_listen(self.user['id'], listened_at + datetime.timedelta(microseconds=500),
                                              msid, record["artist_name"], track_name, additional_info=metadata))
            if i in (7, 8, 15, 16):
                records.append(dict(record))
                expected.append(dict(expected_record))
        self._insert_cache(records)
        listens_db.insert(listens)

        data, _ = self._get_missing_data()

        self.assertEqual(expected, data)

    def test_duplicate_records_preserved(self):
        """ Duplicate cached records keep their order and count and enrich identically. """
        msid = "1e1e1e1e-1e1e-41e1-81e1-1e1e1e1e1e1e"
        record = _cache_record("Duplicate Artist", "Duplicate Track", msid, "2026-11-04T10:00:00.000Z")
        self._insert_cache([record, dict(record)])
        listens_db.insert([
            _stored_listen(self.user['id'], datetime.datetime(2026, 11, 4, 10, 0, 0,
                                                              tzinfo=datetime.timezone.utc),
                           msid, "Duplicate Artist", "Duplicate Track",
                           additional_info={"music_service": "spotify.com"}),
        ])

        data, _ = self._get_missing_data()

        expected = dict(record, additional_info={"music_service": "spotify.com"})
        self.assertEqual([expected, dict(expected)], data)

    def test_more_than_1000_records_chunked_without_loss(self):
        """ Sets larger than one chunk are fully hydrated in their original order. """
        base = datetime.datetime(2026, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        records = []
        listens = []
        msids = []
        for i in range(1001):
            msid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"lb-1053-chunk-{i}"))
            msids.append(msid)
            listened_at = base + datetime.timedelta(seconds=i)
            records.append(_cache_record(f"Chunk Artist {i}", f"Chunk Track {i}", msid,
                                         listened_at.strftime("%Y-%m-%dT%H:%M:%S") + ".000Z"))
            listens.append(_stored_listen(self.user['id'], listened_at, msid,
                                          f"Chunk Artist {i}", f"Chunk Track {i}",
                                          additional_info={"music_service_name": f"Service {i}"}))
        self._insert_cache(records)
        listens_db.insert(listens)

        data, _ = self._get_missing_data()

        self.assertEqual(1001, len(data))
        self.assertEqual(msids, [record["recording_msid"] for record in data])
        for i, record in enumerate(data):
            self.assertEqual({"music_service_name": f"Service {i}"}, record.get("additional_info"))

    def test_reads_do_not_rewrite_cache(self):
        """ Hydrating reads leave the stored cache json and created time untouched. """
        msid = "2f2f2f2f-2f2f-42f2-82f2-2f2f2f2f2f2f"
        record = _cache_record("Cache Artist", "Cache Track", msid, "2026-11-04T10:00:00.000Z")
        self._insert_cache([record])
        listens_db.insert([
            _stored_listen(self.user['id'], datetime.datetime(2026, 11, 4, 10, 0, 0,
                                                              tzinfo=datetime.timezone.utc),
                           msid, "Cache Artist", "Cache Track",
                           additional_info={"music_service": "spotify.com"}),
        ])
        original = self._raw_cache_row()

        data, _ = self._get_missing_data()

        self.assertEqual({"music_service": "spotify.com"}, data[0]["additional_info"])
        reread = self._raw_cache_row()
        self.assertEqual(original["data"], reread["data"])
        self.assertEqual(original["created"], reread["created"])

    def test_cache_edge_cases_return_tuples(self):
        """ Absent, empty and null caches return unpackable results. """
        data, created = self._get_missing_data()
        self.assertIsNone(data)
        self.assertIsNone(created)

        for missing_musicbrainz_data in ([], None):
            db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
                self.db_conn,
                user_id=self.user['id'],
                missing_musicbrainz_data=UserMissingMusicBrainzDataJson(
                    missing_musicbrainz_data=missing_musicbrainz_data),
                source='cf',
            )
            data, created = self._get_missing_data()
            self.assertIsNone(data)
            self.assertIsNotNone(created)

    def test_deleted_source_listen_leaves_record_unenriched(self):
        """ A representative listen deleted from the listens database leaves the
            cached record without service metadata.
        """
        msid = "3a3a3a3a-3a3a-43a3-83a3-3a3a3a3a3a3a"
        record = _cache_record("Deleted Artist", "Deleted Track", msid, "2026-11-04T10:00:00.000Z")
        self._insert_cache([record])
        listens_db.insert([
            _stored_listen(self.user['id'], datetime.datetime(2026, 11, 4, 10, 0, 0,
                                                              tzinfo=datetime.timezone.utc),
                           msid, "Deleted Artist", "Deleted Track",
                           additional_info={"music_service": "spotify.com"}),
        ])

        data, _ = self._get_missing_data()
        self.assertEqual({"music_service": "spotify.com"}, data[0]["additional_info"])

        self.listens_conn.execute(sqlalchemy.text(
            "DELETE FROM listen WHERE user_id = :user_id AND recording_msid = :msid"),
            {"user_id": self.user['id'], "msid": msid})
        self.listens_conn.commit()

        data, _ = self._get_missing_data()
        self.assertEqual([record], data)

    def test_timescale_copy_is_not_used(self):
        """ A matching listen that exists only in the Timescale database must not
            supply service metadata.
        """
        msid = "4b4b4b4b-4b4b-44b4-84b4-4b4b4b4b4b4b"
        record = _cache_record("Timescale Artist", "Timescale Track", msid, "2026-11-04T10:00:00.000Z")
        self._insert_cache([record])
        listened_at = datetime.datetime(2026, 11, 4, 10, 0, 0, tzinfo=datetime.timezone.utc)
        self.ts_conn.execute(sqlalchemy.text("""
            INSERT INTO listen (listened_at, created, user_id, recording_msid, data)
                 VALUES (:listened_at, NOW(), :user_id, :msid, :data)
            """), {
                "listened_at": listened_at,
                "user_id": self.user['id'],
                "msid": msid,
                "data": orjson.dumps({"artist_name": "Timescale Artist",
                                      "track_name": "Timescale Track",
                                      "additional_info": {"music_service": "spotify.com"}}).decode("utf-8"),
            })
        self.ts_conn.commit()

        data, _ = self._get_missing_data()

        self.assertEqual([record], data)
