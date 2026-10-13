import socket
import unittest
import uuid

import requests

from listenbrainz.clickhouse.clickhouse_reader import (
    TransientHandlerError,
    create_clickhouse_reader_couchdb,
    is_retryable,
)
from listenbrainz.clickhouse.testing import ClickHouseReaderTestCase
from listenbrainz.db import couchdb
from listenbrainz.db.couchdb import CouchDBConnection


def http_error(status_code) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status_code
    return requests.HTTPError(response=response)


class IsRetryableTestCase(unittest.TestCase):

    def test_transient_errors(self):
        for error in (requests.ConnectionError(), requests.ReadTimeout(), http_error(503), http_error(429)):
            with self.subTest(error=error):
                self.assertTrue(is_retryable(error))

    def test_permanent_errors(self):
        errors = (http_error(401), http_error(400), requests.JSONDecodeError("bad", "", 0),
                  requests.exceptions.InvalidURL(), FileNotFoundError(), ValueError())
        for error in errors:
            with self.subTest(error=error):
                self.assertFalse(is_retryable(error))


class ClickHouseReaderCallbackTestCase(ClickHouseReaderTestCase):

    def setUp(self):
        super().setUp()
        self.reader.retry_delays = (0, 0)
        self.database = f"test_clickhouse_reader_{uuid.uuid4().hex}"
        self.addCleanup(requests.delete, self._database_url("CLICKHOUSE_READER_COUCHDB_", self.database))

    def _couchdb(self, **overrides) -> CouchDBConnection:
        """A connection like the reader's, with the given attributes changed."""
        connection = create_clickhouse_reader_couchdb(self.app.config)
        for name, value in overrides.items():
            setattr(connection, name, value)
        return connection

    def _silent_server_port(self) -> int:
        """Port of a server accepting connections without ever answering."""
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen()
        self.addCleanup(server.close)
        return server.getsockname()[1]

    def _write_handler(self, connections=None):
        """A handler writing the message's data to the database, through the given connections in turn."""
        attempts = []

        def handler(message, connection):
            if connections:
                connection = connections[min(len(attempts), len(connections) - 1)]
            attempts.append(connection)
            couchdb.try_insert_data(self.database, message["data"], connection=connection)

        return handler, attempts

    def _handle(self, handler):
        self.register_handler("clk_test", handler)
        self.publish_result({"type": "clk_test", "data": [{"_id": "1", "count": 1}]})
        message = self.get_result_message()
        self.reader.callback(message)
        return message

    def _stored_count(self):
        return requests.get(f"{self._database_url('CLICKHOUSE_READER_COUCHDB_', self.database)}/1").json()["count"]

    def test_transient_couchdb_errors_are_retried_in_place(self):
        unreachable = self._couchdb(port=1)
        silent = self._couchdb(host="127.0.0.1", port=self._silent_server_port(), timeout=(1, 0.2))
        for failing in (unreachable, silent):
            with self.subTest(host=failing.host, port=failing.port):
                handler, attempts = self._write_handler([failing, self.reader.couchdb])

                self._handle(handler)

                self.assertEqual(attempts, [failing, self.reader.couchdb])
                self.assertEqual(self._stored_count(), 1)
                self.assertEqual(self.queued_result_count(), 0)
        self.assertEqual(self.reported_exceptions(), [])

    def test_message_failing_transiently_on_every_attempt_is_left_unacked(self):
        self.reader.couchdb = self._couchdb(port=1)
        handler, attempts = self._write_handler()

        with self.assertRaises(TransientHandlerError):
            self._handle(handler)

        self.assertEqual(len(attempts), len(self.reader.retry_delays) + 1)
        self.assertEqual(self.reported_exceptions(), ["TransientHandlerError"])
        # once the restarting consumer's connection closes, the broker requeues it in place
        self.connection.release()
        self.connection = self.connection.clone()
        self.result_queue = self.result_queue(self.connection.default_channel)
        message = self.get_result_message()
        self.assertIsNotNone(message)
        self.assertTrue(message.delivery_info["redelivered"])
        message.ack()

    def test_permanent_errors_are_reported_and_acked(self):
        self.reader.couchdb = self._couchdb(admin_key="wrong")
        handler, attempts = self._write_handler()
        self._handle(handler)
        self.assertEqual(len(attempts), 1)

        def buggy_handler(message, connection):
            return message["missing"]

        self._handle(buggy_handler)

        self.assertEqual(self.queued_result_count(), 0)
        self.assertEqual(self.reported_exceptions(), ["HTTPError", "KeyError"])

    def test_handlers_write_to_clickhouse_reader_couchdb(self):
        handler, _ = self._write_handler()

        self._handle(handler)

        self.assertEqual(self.queued_result_count(), 0)
        self.assertEqual(self._stored_count(), 1)
        self.assertEqual(requests.get(self._database_url("COUCHDB_", self.database)).status_code, 404)
        # the reader leaves the default connection used by the rest of LB alone
        self.assertEqual(couchdb.get_base_url(), self._base_url("COUCHDB_"))

    def test_reader_couchdb_connection_has_a_timeout(self):
        self.assertIsNotNone(self.reader.couchdb.timeout)

    def _base_url(self, config_prefix):
        config = self.app.config
        return (
            f"http://{config[config_prefix + 'USER']}:{config[config_prefix + 'ADMIN_KEY']}"
            f"@{config[config_prefix + 'HOST']}:{config[config_prefix + 'PORT']}"
        )

    def _database_url(self, config_prefix, database):
        return f"{self._base_url(config_prefix)}/{self.app.config['COUCHDB_DATABASE_PREFIX']}{database}"
