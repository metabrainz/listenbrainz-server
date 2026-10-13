import calendar
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

import pyarrow.parquet as pq

from clickhouse.stats.activity_cache_manager import ActivityStatsCacheManager, BulkActivityStatsCacheManager
from clickhouse.stats.cache_manager import TIME_RANGES, mark_users_for_recompute
from clickhouse.tests import ClickHouseTestCase, TEST_DATA_PATH


class ActivityDataTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        self.load_spark_listens()

    def test_full_refresh_matches_spark_expected_files(self):
        for entity in ("daily_activity", "listening_activity"):
            with self.subTest(entity=entity):
                expected = json.loads((TEST_DATA_PATH / f"user_{entity}_all_time.json").read_text())[0]
                manager = self.manager(BulkActivityStatsCacheManager, entity)
                messages = list(manager.run_full_refresh(message_batch_size=1, user_flush_size=1))
                all_time = [m for m in messages if m.get("stats_range") == "all_time" and m["type"] == "clk_user_entity"]
                actual = {u["user_id"]: u["data"] for m in all_time for u in m["data"]}
                self.assertEqual(set(actual), {u["user_id"] for u in expected["data"]})
                for user in expected["data"]:
                    self.assertCountEqual(actual[user["user_id"]], user["data"])
                for message in all_time:
                    self.assertEqual(message["from_ts"], expected["from_ts"])
                    self.assertEqual(message["to_ts"], expected["to_ts"])
                    self.assertEqual(len(message["data"]), 1)
                self.assertEqual(set(manager.get_cache_state()), set(TIME_RANGES))
                self.assertEqual(self.client.query(
                    "SELECT count() FROM system.tables WHERE database = currentDatabase() AND name LIKE 'tmp_bulk_%'"
                ).first_row[0], 0)
                # The full job must persist cache state that the incremental job can use.
                incremental = self.manager(ActivityStatsCacheManager, entity)
                self.assertEqual(list(incremental.run_hourly_job()), [])

    def test_all_ranges_against_independent_fixture_counts(self):
        # These bounds are fixed for the fixture's latest listen, 2021-08-09.
        # Do not use the production range selector to construct the oracle.
        daily_bounds = {
            "all_time": ("2002-01-01", "2021-08-09T12:22:43"),
            "this_week": ("2021-08-02", "2021-08-09"),
            "this_month": ("2021-08-01", "2021-09-01"),
            "this_year": ("2021-01-01", "2022-01-01"),
            "week": ("2021-08-02", "2021-08-09"),
            "month": ("2021-07-01", "2021-08-01"),
            "quarter": ("2021-04-01", "2021-07-01"),
            "half_yearly": ("2021-01-01", "2021-07-01"),
            "year": ("2020-01-01", "2021-01-01"),
        }
        listening_bounds = {
            "all_time": daily_bounds["all_time"],
            "this_week": ("2021-07-26", "2021-08-09"),
            "this_month": ("2021-07-01", "2021-08-09"),
            "this_year": ("2020-01-01", "2021-08-09"),
            "week": ("2021-07-26", "2021-08-09"),
            "month": ("2021-06-01", "2021-08-01"),
            "quarter": ("2021-01-01", "2021-07-01"),
            "half_yearly": ("2020-07-01", "2021-07-01"),
            "year": ("2019-01-01", "2021-01-01"),
        }
        rows = [row for name in ("full-dump-1", "incremental-dump-2", "incremental-dump-3")
                for path in (TEST_DATA_PATH / name).glob("*.parquet") for row in pq.read_table(path).to_pylist()]
        listens = {(r["user_id"], r["listened_at"], r["recording_msid"]) for r in rows}
        for entity, bounds in (("daily_activity", daily_bounds), ("listening_activity", listening_bounds)):
            incremental = self.manager(ActivityStatsCacheManager, entity)
            bulk = self.manager(BulkActivityStatsCacheManager, entity)
            bulk.build_intermediate_table()
            for stats_range, (start, end) in bounds.items():
                with self.subTest(entity=entity, stats_range=stats_range):
                    start, end = datetime.fromisoformat(start), datetime.fromisoformat(end)
                    inclusive = entity == "daily_activity" or stats_range == "all_time"
                    selected = [(uid, ts) for uid, ts, _ in listens
                                if start <= ts and (ts <= end if inclusive else ts < end)]
                    result = incremental.compute_activity_batch(stats_range, [1, 2, 999])
                    streamed = dict(bulk.stream_activity_for_range(stats_range))
                    self.assertEqual(set(result), {uid for uid, _ in selected})
                    self.assertEqual(set(streamed), set(result))
                    for uid, entries in result.items():
                        self.assertCountEqual(entries, streamed[uid])
                        timestamps = [ts for user, ts in selected if user == uid]
                        if entity == "daily_activity":
                            counts = Counter((calendar.day_name[ts.weekday()], ts.hour) for ts in timestamps)
                            self.assertCountEqual(entries, [
                                {"day": day, "hour": hour, "listen_count": count}
                                for (day, hour), count in counts.items()
                            ])
                        else:
                            self.assertEqual(sum(e["listen_count"] for e in entries), len(timestamps))
                            self.assertEqual(entries[0]["from_ts"], int(start.replace(tzinfo=timezone.utc).timestamp()))
                            for previous, following in zip(entries, entries[1:]):
                                self.assertEqual(previous["to_ts"] + 1, following["from_ts"])
                            for entry in entries:
                                count = sum(entry["from_ts"] <= int(ts.replace(tzinfo=timezone.utc).timestamp())
                                            <= entry["to_ts"] for ts in timestamps)
                                self.assertEqual(entry["listen_count"], count)
            bulk.drop_intermediate_table()

    def test_incremental_refresh_only_emits_changed_users(self):
        manager = self.manager(ActivityStatsCacheManager, "daily_activity")
        first = list(manager.run_hourly_job(batch_size=1))
        self.assertTrue(first)
        self.assertEqual(list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job()), [])
        self.insert_listens([(1, datetime(2021, 8, 7, 8), datetime(2022, 1, 1), "new-listen")])
        messages = list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        self.assertTrue(messages)
        self.assertEqual({u["user_id"] for m in messages for u in m.get("data", [])}, {1})
        all_time = next(m for m in messages if m.get("stats_range") == "all_time")
        original = next(m for m in first if m["type"] == "clk_user_entity"
                        and m["stats_range"] == "all_time" and m["data"][0]["user_id"] == 1)
        self.assertEqual(sum(e["listen_count"] for e in all_time["data"][0]["data"]),
                         1 + sum(e["listen_count"] for e in original["data"][0]["data"]))


class ActivityBoundaryTestCase(ClickHouseTestCase):
    def test_stale_users_are_scoped_to_range_and_stat_type(self):
        self.insert_listens([
            (1, datetime(2021, 7, 15), datetime(2021, 7, 15), "july"),
            (2, datetime(2021, 8, 15), datetime(2021, 8, 15), "august"),
        ])
        daily = self.manager(ActivityStatsCacheManager, "daily_activity")
        bounds = daily.get_period_bounds("month")
        self.assertEqual(daily.get_stale_users("month", *bounds), [1])
        daily.update_user_cache_state([1], "month", datetime(2021, 8, 15))
        self.assertEqual(daily.get_stale_users("month", *bounds), [])
        self.insert_listens([(1, datetime(2021, 8, 1), datetime(2021, 8, 16), "boundary")])
        # Daily activity includes the period's ending midnight.
        self.assertEqual(daily.get_stale_users("month", *bounds), [1])
        daily.update_user_cache_state([1], "month", datetime(2021, 8, 16))
        # A new listen outside July must not invalidate July daily stats.
        self.insert_listens([(1, datetime(2021, 8, 2), datetime(2021, 8, 17), "outside")])
        self.assertEqual(daily.get_stale_users("month", *bounds), [])
        listening = self.manager(ActivityStatsCacheManager, "listening_activity")
        self.assertEqual(listening.get_stale_users("month", *listening.get_period_bounds("month")), [1])
        daily.clear_user_cache_state_for_time_range("week")
        self.assertEqual(daily.get_stale_users("month", *bounds), [])

    def test_first_run_writes_every_range_to_a_new_database(self):
        # Only July listens: this_week, week etc. have no users, but their (possibly
        # older) databases must still be replaced rather than appended to.
        self.insert_listens([(1, datetime(2021, 7, 15), datetime(2021, 7, 15), "july")])
        messages = list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        for time_range in TIME_RANGES:
            with self.subTest(time_range=time_range):
                types = [m["type"] for m in messages if m.get("time_range", m.get("stats_range")) == time_range]
                self.assertEqual(types[0], "clk_stats_database_start")
                self.assertEqual(types[-1], "clk_stats_database_end")
        data = [m for m in messages if m["type"] == "clk_user_entity"]
        self.assertTrue(data)
        self.assertTrue(all("database" in m and "database_prefix" not in m for m in data))

    def test_rollover_waits_for_cache_state_clear(self):
        # User 1 was computed for June with a cache state newer than their July listen;
        # when month rolls over to July the old state must be gone before stale users are read.
        self.insert_listens([(1, datetime(2021, 6, 15), datetime(2021, 7, 20), "june"),
                             (1, datetime(2021, 7, 15), datetime(2021, 7, 16), "july"),
                             (2, datetime(2021, 8, 9), datetime(2021, 8, 9), "latest")])
        daily = self.manager(ActivityStatsCacheManager, "daily_activity")
        daily.update_cache_state("month", datetime(2021, 6, 1).date(), datetime(2021, 7, 20),
                                 daily.get_activity_range("month").to_ts)
        daily.update_user_cache_state([1], "month", datetime(2021, 7, 20))
        messages = [m for m in daily.run_hourly_job() if m.get("stats_range") == "month"]
        self.assertEqual({u["user_id"] for m in messages for u in m["data"]}, {1})

    def test_moved_range_end_rebuilds_users_without_new_listens(self):
        self.insert_listens([(1, datetime(2021, 8, 2, 10), datetime(2021, 8, 2, 10), "monday"),
                             (2, datetime(2021, 8, 3, 10), datetime(2021, 8, 3, 10), "tuesday")])
        list(self.manager(ActivityStatsCacheManager, "listening_activity").run_hourly_job())
        # Only user 2 listens again, a day later: the this_week range now ends a day later.
        self.insert_listens([(2, datetime(2021, 8, 4, 10), datetime(2021, 8, 4, 10), "wednesday")])
        messages = list(self.manager(ActivityStatsCacheManager, "listening_activity").run_hourly_job())
        this_week = [m for m in messages if m.get("time_range", m.get("stats_range")) == "this_week"]
        self.assertEqual([this_week[0]["type"], this_week[-1]["type"]],
                         ["clk_stats_database_start", "clk_stats_database_end"])
        users = {u["user_id"]: (m["to_ts"], u["data"]) for m in this_week if m["type"] == "clk_user_entity"
                 for u in m["data"]}
        self.assertEqual(set(users), {1, 2})
        to_ts, buckets = users[1]
        self.assertEqual(to_ts, int(datetime(2021, 8, 4, tzinfo=timezone.utc).timestamp()))
        self.assertEqual(buckets[-1]["to_ts"] + 1, to_ts)
        # Nothing moved since: the next run has nothing to do.
        self.assertEqual(list(self.manager(ActivityStatsCacheManager, "listening_activity").run_hourly_job()), [])

    def test_forced_users_without_listens_get_empty_stats(self):
        self.insert_listens([(1, datetime(2021, 7, 15), datetime(2021, 7, 15), "july"),
                             (2, datetime(2021, 8, 9), datetime(2021, 8, 9), "latest")])
        list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        self.client.command("DELETE FROM listens WHERE user_id = 1")
        mark_users_for_recompute(self.client, "SELECT 1")
        messages = list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        users = {(m["stats_range"], u["user_id"]): u for m in messages for u in m.get("data", [])}
        self.assertEqual(users[("month", 1)], {"user_id": 1, "count": 0, "data": []})
        self.assertEqual(users[("all_time", 1)]["data"], [])
        self.assertNotIn(2, {user_id for _, user_id in users})
        self.assertEqual(list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job()), [])

    def test_empty_database_produces_no_stats(self):
        for entity in ("daily_activity", "listening_activity"):
            self.assertEqual(list(self.manager(BulkActivityStatsCacheManager, entity).run_full_refresh()), [])
            self.assertEqual(list(self.manager(ActivityStatsCacheManager, entity).run_hourly_job()), [])

    def test_midnight_bounds_and_utc_weekday(self):
        start = datetime(2021, 7, 1, tzinfo=timezone.utc)
        end = datetime(2021, 8, 1, tzinfo=timezone.utc)
        timestamps = [start - timedelta(milliseconds=1), start, end - timedelta(milliseconds=1), end,
                      end + timedelta(milliseconds=1)]
        self.insert_listens([(1, ts, ts, str(i)) for i, ts in enumerate(timestamps)] + [
            (2, datetime(2021, 8, 9, tzinfo=timezone.utc), end, "latest"),
        ])
        daily = self.manager(ActivityStatsCacheManager, "daily_activity").compute_activity_batch("month", [1])
        self.assertCountEqual(daily[1], [
            {"day": "Thursday", "hour": 0, "listen_count": 1},
            {"day": "Saturday", "hour": 23, "listen_count": 1},
            {"day": "Sunday", "hour": 0, "listen_count": 1},
        ])
        listening = self.manager(ActivityStatsCacheManager, "listening_activity").compute_activity_batch("month", [1])
        self.assertEqual(len(listening[1]), 61)
        self.assertEqual(sum(e["listen_count"] for e in listening[1]), 3)
        self.assertEqual(listening[1][-1]["listen_count"], 1)

    def test_period_rollover_recomputes_existing_users(self):
        self.insert_listens([(1, datetime(2021, 7, 15), datetime(2021, 7, 15), "july"),
                             (3, datetime(2021, 6, 15), datetime(2021, 6, 15), "june")])
        list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        self.insert_listens([(2, datetime(2021, 8, 15), datetime(2021, 8, 15), "august")])
        messages = list(self.manager(ActivityStatsCacheManager, "daily_activity").run_hourly_job())
        month = [m for m in messages if m.get("stats_range") == "month"]
        data = [m for m in month if m["type"] == "clk_user_entity"]
        self.assertEqual({u["user_id"] for m in data for u in m["data"]}, {1})
        self.assertIn("database", data[0])
        self.assertEqual(self.manager(ActivityStatsCacheManager, "daily_activity").get_cache_state()["month"]["period_start"],
                         datetime(2021, 7, 1).date())
