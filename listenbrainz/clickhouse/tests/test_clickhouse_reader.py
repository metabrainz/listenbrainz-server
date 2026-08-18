import unittest
from unittest import mock

from flask import Flask

from listenbrainz.clickhouse.clickhouse_reader import (
    ClickHouseReader,
    init_clickhouse_reader_couchdb,
)


class ClickHouseReaderTestCase(unittest.TestCase):

    def _app(self):
        app = Flask(__name__)
        app.config.update({
            "CLICKHOUSE_RESULT_EXCHANGE": "clickhouse_result",
            "CLICKHOUSE_RESULT_QUEUE": "clickhouse_result",
            "COUCHDB_HOST": "regular-couchdb",
            "COUCHDB_PORT": 5984,
            "COUCHDB_USER": "regular-user",
            "COUCHDB_ADMIN_KEY": "regular-password",
            "COUCHDB_DATABASE_PREFIX": "test_",
            "CLICKHOUSE_READER_COUCHDB_HOST": "clickhouse-reader-couchdb",
            "CLICKHOUSE_READER_COUCHDB_PORT": 15984,
            "CLICKHOUSE_READER_COUCHDB_USER": "clickhouse-reader-user",
            "CLICKHOUSE_READER_COUCHDB_ADMIN_KEY": "clickhouse-reader-password",
        })
        return app

    @mock.patch("listenbrainz.clickhouse.clickhouse_reader.couchdb.init")
    def test_init_uses_clickhouse_reader_couchdb_config(self, mock_couchdb_init):
        init_clickhouse_reader_couchdb(self._app())

        mock_couchdb_init.assert_called_once_with(
            "clickhouse-reader-user",
            "clickhouse-reader-password",
            "clickhouse-reader-couchdb",
            15984,
            "test_",
        )

    @mock.patch("listenbrainz.clickhouse.clickhouse_reader.init_clickhouse_reader_couchdb")
    def test_reader_initializes_clickhouse_reader_couchdb(self, mock_init):
        app = self._app()
        ClickHouseReader(app)
        mock_init.assert_called_once_with(app)

    def test_init_requires_clickhouse_reader_couchdb_config(self):
        app = self._app()
        del app.config["CLICKHOUSE_READER_COUCHDB_HOST"]
        with self.assertRaises(KeyError):
            init_clickhouse_reader_couchdb(app)

    def test_init_rejects_unconfigured_host(self):
        for host in ["", "KEYDOESNOTEXIST_clickhouse_reader_couchdb_host", "SERVICEDOESNOTEXIST_couchdb-clickhouse"]:
            with self.subTest(host=host):
                app = self._app()
                app.config["CLICKHOUSE_READER_COUCHDB_HOST"] = host
                with self.assertRaisesRegex(RuntimeError, "CLICKHOUSE_READER_COUCHDB_HOST"):
                    init_clickhouse_reader_couchdb(app)

    @mock.patch("listenbrainz.clickhouse.clickhouse_reader.couchdb.init")
    def test_reader_uses_result_exchange_and_queue(self, _mock_init):
        reader = ClickHouseReader(self._app())

        self.assertEqual(reader.clickhouse_result_exchange.name, "clickhouse_result")
        self.assertEqual(reader.clickhouse_result_queue.name, "clickhouse_result")


if __name__ == "__main__":
    unittest.main()
