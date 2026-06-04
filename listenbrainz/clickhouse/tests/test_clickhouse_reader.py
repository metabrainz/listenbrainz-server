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

    def test_init_rejects_missing_consul_values(self):
        app = self._app()
        app.config["CLICKHOUSE_READER_COUCHDB_HOST"] = (
            "KEYDOESNOTEXIST_clickhouse_reader_couchdb_host"
        )

        with self.assertRaisesRegex(RuntimeError, "CLICKHOUSE_READER_COUCHDB_HOST"):
            init_clickhouse_reader_couchdb(app)

    def test_init_rejects_missing_consul_service_values(self):
        app = self._app()
        app.config["CLICKHOUSE_READER_COUCHDB_HOST"] = (
            "SERVICEDOESNOTEXIST_couchdb-clickhouse"
        )

        with self.assertRaisesRegex(RuntimeError, "CLICKHOUSE_READER_COUCHDB_HOST"):
            init_clickhouse_reader_couchdb(app)


if __name__ == "__main__":
    unittest.main()
