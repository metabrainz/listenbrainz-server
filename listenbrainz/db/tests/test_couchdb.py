import json
import unittest
from io import BytesIO
from unittest.mock import patch

import requests

from listenbrainz import config
from listenbrainz.db import couchdb
from listenbrainz.db.couchdb import get_base_url, DATABASE_LOCK_FILE
from listenbrainz.db.tests.utils import delete_all_couch_databases


class CouchdbTestCase(unittest.TestCase):

    def setUp(self) -> None:
        couchdb.init(config.COUCHDB_USER, config.COUCHDB_ADMIN_KEY, config.COUCHDB_HOST, config.COUCHDB_PORT)

    def tearDown(self) -> None:
        delete_all_couch_databases()

    def test_lock_unlock_delete(self):
        # delete ignore the latest database thus creating 1 extra here
        # so that we can actually test functions
        couchdb.create_database("couchdb_test_db_20220731")

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

    @patch("listenbrainz.db.couchdb.unlock_database", wraps=couchdb.unlock_database)
    @patch("listenbrainz.db.couchdb.lock_database", wraps=couchdb.lock_database)
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

        dumped = BytesIO()
        couchdb.dump_database("couchdb_dump_test_db", dumped)
        dumped.seek(0)
        received = dumped.read().splitlines()

        self.assertEqual({"data": "foo"}, json.loads(received[0]))
        self.assertEqual({"data": "bar"}, json.loads(received[1]))

        mock_lock.assert_called_with(database)
        mock_unlock.assert_called_with(database)

    def test_insert_new_data_overwrites_conflicts(self):
        database = "couchdb_dump_test_db_20240204"
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

        couchdb.insert_data(database, [
            {
                "_id": "1",
                "data": "baz"
            },
            {
                "_id": "3",
                "data": "foobar"
            }
        ])

        dumped = BytesIO()
        couchdb.dump_database("couchdb_dump_test_db", dumped)
        dumped.seek(0)
        received = dumped.read().splitlines()
        print(received)

        response = couchdb.fetch_data(database, 1)
        self.assertEqual(response["data"], "baz")
        response = couchdb.fetch_data(database, 2)
        self.assertEqual(response["data"], "bar")
        response = couchdb.fetch_data(database, 3)
        self.assertEqual(response["data"], "foobar")

    def test_dump_pagination(self):
        database = "couchdb_dump_pagination_test_db_20250505"
        couchdb.create_database(database)

        numbers = list(range(1000))
        docs = []
        for i in numbers:
            docs.append({"_id": str(i), "key": str(i), "data": i})
        couchdb.insert_data(database, docs)

        dumped = BytesIO()
        couchdb.dump_database("couchdb_dump_pagination_test_db", dumped)
        dumped.seek(0)
        received = dumped.read().splitlines()
        received_numbers = {json.loads(x)["data"] for x in received}
        self.assertEqual(set(numbers), received_numbers)
