import unittest
from io import StringIO
from unittest.mock import patch

import requests
import ujson

from listenbrainz import config
from listenbrainz.db import couchdb
from listenbrainz.db.couchdb import get_base_url, DATABASE_LOCK_FILE


class CouchdbTestCase(unittest.TestCase):

    def setUp(self) -> None:
        couchdb.init(config.COUCHDB_USER, config.COUCHDB_ADMIN_KEY, config.COUCHDB_HOST, config.COUCHDB_PORT)

    def test_lock_unlock_delete(self):
        database = "couchdb_test_db_20220730"
        couchdb.create_database(database)

        couchdb.lock_database(database)
        databases_url = f"{get_base_url()}/{database}"
        response = requests.get(f"{databases_url}/{DATABASE_LOCK_FILE}")
        self.assertEqual(response.status_code, 200)

        deleted, retained = couchdb.delete_database("couchdb_test_db")
        self.assertEqual(deleted, [])
        self.assertEqual(retained, [database])

        couchdb.unlock_database(database)
        databases_url = f"{get_base_url()}/{database}"
        response = requests.get(f"{databases_url}/{DATABASE_LOCK_FILE}")
        self.assertEqual(response.status_code, 404)

        deleted, retained = couchdb.delete_database("couchdb_test_db")
        self.assertEqual(deleted, [database])
        self.assertEqual(retained, [])

    @patch("couchdb.unlock_database", wraps=couchdb.unlock_database)
    @patch("couchdb.lock_database", wraps=couchdb.lock_database)
    def test_dump(self, mock_lock, mock_unlock):
        database = "couchdb_dump_test_db_20220730"
        couchdb.create_database(database)
        couchdb.insert_data(database, [
            {
                "_id": "1",
                "data": "foo"
            },
            {
                "_id": "2",
                "data": "bar"
            }
        ])

        dumped = StringIO()
        couchdb.dump_database("couchdb_dump_test_db", dumped)
        received = ujson.loads("[" + dumped.read() + "]")
        self.assertEqual([{"data": "foo"}, {"data": "bar"}], received)

        mock_lock.assert_called_with(database)
        mock_unlock.assert_called_with(database)
