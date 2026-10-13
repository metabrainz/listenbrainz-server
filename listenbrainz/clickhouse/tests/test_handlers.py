import json
import os
from datetime import datetime
from unittest import mock
from uuid import uuid4

import requests
from flask import Flask

from clickhouse import config
from clickhouse.request_consumer import ClickHouseRequestConsumer
from clickhouse.tests import ClickHouseTestCase, TEST_DATA_PATH
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz.db import couchdb, stats
from listenbrainz.clickhouse.handlers import (
    handle_stats_database_end,
    handle_stats_database_start,
    handle_user_entity_stats,
)


class ClickHouseHandlerTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        context = Flask(__name__).app_context()
        context.push()
        self.addCleanup(context.pop)
        connection = couchdb.CouchDBConnection(
            os.environ.get("CLICKHOUSE_TEST_COUCHDB_USER", "listenbrainz"),
            os.environ.get("CLICKHOUSE_TEST_COUCHDB_PASSWORD", "listenbrainz"),
            os.environ.get("CLICKHOUSE_TEST_COUCHDB_HOST", "couchdb"),
            int(os.environ.get("CLICKHOUSE_TEST_COUCHDB_PORT", "5984")),
            "test_clickhouse_" + uuid4().hex + "_",
        )
        # Swap connection configuration, never the database operations themselves.
        for module, attribute in ((couchdb, "_default_connection"), (stats, "_clickhouse_couchdb")):
            patcher = mock.patch.object(module, attribute, connection)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.drop_databases, connection)
        self.database = "clk_daily_activity_all_time_20240101"

    @staticmethod
    def drop_databases(connection):
        for database in couchdb.list_databases("", connection=connection):
            requests.delete(connection.get_database_url(database)).raise_for_status()

    def message(self, **kwargs):
        return {
            "type": "clk_user_entity", "entity": "daily_activity", "stats_range": "all_time",
            "from_ts": 1, "to_ts": 2, "database_prefix": "clk_daily_activity_all_time",
            "data": [{"user_id": 42, "count": 1, "data": [{"day": "Monday", "hour": 8, "listen_count": 5}]}],
            **kwargs,
        }

    def test_database_lifecycle_keeps_latest_and_locked_databases(self):
        for suffix in ("20240101", "20240102", "20240103"):
            handle_stats_database_start({"database": "clk_daily_activity_all_time_" + suffix})
        couchdb.insert_data(self.database, [{"_id": "LOCK"}])
        handle_stats_database_end({"database": "clk_daily_activity_all_time_20240103"})
        self.assertEqual(couchdb.list_databases("clk_daily_activity_all_time"), [
            "clk_daily_activity_all_time_20240103", self.database,
        ])

    def test_prefix_resolution_and_upsert(self):
        handle_stats_database_start({"database": self.database})
        handle_user_entity_stats(self.message())
        first = couchdb.fetch_data("clk_daily_activity_all_time", 42)
        self.assertEqual(first["data"], [{"day": "Monday", "hour": 8, "listen_count": 5}])
        self.assertEqual((first["from_ts"], first["to_ts"]), (1, 2))
        message = self.message()
        message["data"][0]["data"][0]["listen_count"] = 7
        handle_user_entity_stats(message)
        updated = couchdb.fetch_data("clk_daily_activity_all_time", 42)
        self.assertEqual(updated["data"][0]["listen_count"], 7)
        self.assertNotEqual(updated["_rev"], first["_rev"])
        self.assertEqual(couchdb.list_databases("clk_daily_activity_all_time"), [self.database])

    def test_invalid_entries_are_filtered_and_count_is_corrected(self):
        message = self.message()
        message["data"][0]["count"] = 2
        message["data"][0]["data"].append({"day": "Monday", "listen_count": 6})
        handle_user_entity_stats(message)
        document = couchdb.fetch_data("clk_daily_activity_all_time", 42)
        self.assertEqual(document["count"], 1)
        self.assertEqual(document["data"], [{"day": "Monday", "hour": 8, "listen_count": 5}])
        self.assertEqual(len(couchdb.list_databases("")), 1)

    def test_empty_stats_replace_document_and_are_served_as_none(self):
        handle_user_entity_stats(self.message())
        self.assertIsNotNone(stats.get(42, "clk_daily_activity", "all_time", DailyActivityRecord, clickhouse=True))
        handle_user_entity_stats(self.message(data=[{"user_id": 42, "count": 0, "data": []}]))
        self.assertEqual(couchdb.fetch_data("clk_daily_activity_all_time", 42)["data"], [])
        self.assertIsNone(stats.get(42, "clk_daily_activity", "all_time", DailyActivityRecord, clickhouse=True))

    def test_couchdb_errors_propagate(self):
        unreachable = couchdb.CouchDBConnection("user", "password", "127.0.0.1", 1, "")
        with mock.patch.object(couchdb, "_default_connection", unreachable):
            with self.assertRaises(requests.ConnectionError):
                handle_user_entity_stats(self.message())
            with self.assertRaises(requests.ConnectionError):
                handle_stats_database_start({"database": self.database})

    def test_unsupported_entity_does_not_create_database(self):
        handle_user_entity_stats(self.message(entity="artists", database_prefix="clk_artists_all_time"))
        self.assertEqual(couchdb.list_databases(""), [])

    def test_request_to_clickhouse_to_couchdb_matches_spark_fixtures(self):
        self.load_spark_listens()
        settings = {"CLICKHOUSE_" + key.upper(): value for key, value in self.connection.items()}
        consumer = ClickHouseRequestConsumer()
        dispatch = {
            "clk_stats_database_start": handle_stats_database_start,
            "clk_stats_database_end": handle_stats_database_end,
            "clk_user_entity": handle_user_entity_stats,
        }
        with mock.patch.multiple(config, **settings):
            messages = list(consumer.get_result({"query": "clickhouse.stats.full_refresh"}))
            self.assertEqual(messages[-1]["type"], "clk_stats_complete")
            self.assertFalse(any(m["type"] == "clk_stats_error" for m in messages), messages)
            for message in messages:
                if message["type"] in dispatch:
                    dispatch[message["type"]](json.loads(json.dumps(message)))
            for entity, model in (("daily_activity", DailyActivityRecord), ("listening_activity", ListeningActivityRecord)):
                expected = json.loads((TEST_DATA_PATH / f"user_{entity}_all_time.json").read_text())[0]
                for user in expected["data"]:
                    result = stats.get(user["user_id"], entity, "all_time", model, clickhouse=True)
                    self.assertIsNotNone(result)
                    self.assertCountEqual(json.loads(result.data.json()), user["data"])
                    self.assertEqual((result.from_ts, result.to_ts), (expected["from_ts"], expected["to_ts"]))
            # Incremental messages update existing CouchDB documents, including revisions.
            before = couchdb.fetch_data("daily_activity_all_time", 1)
            self.insert_listens([(1, datetime(2021, 8, 7, 8), datetime(2022, 1, 1), "new")])
            for message in consumer.get_result({"query": "clickhouse.stats.hourly", "params": {"entity": "daily_activity"}}):
                if message["type"] in dispatch:
                    dispatch[message["type"]](json.loads(json.dumps(message)))
            after = couchdb.fetch_data("daily_activity_all_time", 1)
            self.assertEqual(sum(r["listen_count"] for r in after["data"]), 1 + sum(r["listen_count"] for r in before["data"]))
            self.assertNotEqual(after["_rev"], before["_rev"])
