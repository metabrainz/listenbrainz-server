import json
import listenbrainz.db.missing_musicbrainz_data as db_missing_musicbrainz_data
import listenbrainz.db.user as db_user

from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataJson
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase


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
            self.db_conn, self.ts_conn, user_id=self.user['id'], source='cf'
        )
        self.assertEqual(missing_musicbrainz_data, result[0])

    def test_get_user_missing_musicbrainz_data(self):
        data_inserted = self.insert_test_data()
        result = db_missing_musicbrainz_data.get_user_missing_musicbrainz_data(
            self.db_conn, self.ts_conn, user_id=self.user['id'], source='cf'
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
            self.db_conn, self.ts_conn, user_id=self.user['id'], source='cf'
        )
        self.assertIsNone(result)
