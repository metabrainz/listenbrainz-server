import unittest
from unittest import mock

from flask import Flask

from listenbrainz.clickhouse.handlers import (
    handle_stats_database_end,
    handle_stats_database_start,
    handle_user_entity_stats,
)


class ClickHouseHandlerTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    @mock.patch("listenbrainz.clickhouse.handlers.couchdb.create_database")
    def test_handle_stats_database_start_accepts_clickhouse_prefixed_database(self, mock_create_database):
        handle_stats_database_start({
            "type": "clk_stats_database_start",
            "database": "clk_artists_all_time_20240101",
        })

        mock_create_database.assert_called_once_with("clk_artists_all_time_20240101")

    @mock.patch("listenbrainz.clickhouse.handlers.couchdb.delete_database")
    def test_handle_stats_database_end_uses_clickhouse_prefixed_database_prefix(self, mock_delete_database):
        mock_delete_database.return_value = ([], [])

        handle_stats_database_end({
            "type": "clk_stats_database_end",
            "database": "clk_artists_all_time_20240101",
        })

        mock_delete_database.assert_called_once_with("clk_artists_all_time")

    @mock.patch("listenbrainz.clickhouse.handlers.db_stats.insert")
    @mock.patch("listenbrainz.clickhouse.handlers.couchdb.list_databases")
    def test_handle_user_entity_stats_resolves_database_prefix(self, mock_list_databases, mock_insert):
        mock_list_databases.return_value = ["clk_artists_all_time_20240101"]

        handle_user_entity_stats({
            "type": "clk_user_entity",
            "entity": "artists",
            "stats_range": "all_time",
            "from_ts": 1,
            "to_ts": 2,
            "database_prefix": "clk_artists_all_time",
            "data": [{
                "user_id": 42,
                "count": 1,
                "data": [{
                    "artist_name": "An Artist",
                    "listen_count": 5,
                }],
            }],
        })

        mock_insert.assert_called_once_with(
            "clk_artists_all_time_20240101",
            1,
            2,
            [{
                "user_id": 42,
                "count": 1,
                "data": [{
                    "artist_name": "An Artist",
                    "listen_count": 5,
                }],
            }],
        )

    @mock.patch("listenbrainz.clickhouse.handlers.db_stats.insert")
    def test_handle_user_entity_stats_drops_invalid_entries(self, mock_insert):
        handle_user_entity_stats({
            "type": "clk_user_entity",
            "entity": "artists",
            "stats_range": "all_time",
            "from_ts": 1,
            "to_ts": 2,
            "database": "clk_artists_all_time_20240101",
            "data": [{
                "user_id": 42,
                "count": 2,
                "data": [
                    {"artist_name": "An Artist", "listen_count": 5},
                    {"artist_name": "", "listen_count": 6},
                ],
            }],
        })

        mock_insert.assert_called_once_with(
            "clk_artists_all_time_20240101",
            1,
            2,
            [{
                "user_id": 42,
                "count": 1,
                "data": [{"artist_name": "An Artist", "listen_count": 5}],
            }],
        )


if __name__ == "__main__":
    unittest.main()
