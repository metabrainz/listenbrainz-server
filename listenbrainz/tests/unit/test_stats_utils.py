import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from dateutil.relativedelta import relativedelta

from listenbrainz.webserver.views.stats_utils import current_period_listen_count


def _ts(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def _record(from_ts: int, listen_count: int) -> SimpleNamespace:
    # current_period_listen_count only needs from_ts and listen_count, which
    # ListeningActivityRecord also exposes.
    return SimpleNamespace(from_ts=from_ts, listen_count=listen_count)


def _daily(start: datetime, counts):
    """ One daily segment per count, starting at ``start``. """
    return [_record(_ts(start + relativedelta(days=i)), c) for i, c in enumerate(counts)]


def _monthly(start: datetime, counts):
    """ One monthly segment per count, starting at ``start``. """
    return [_record(_ts(start + relativedelta(months=i)), c) for i, c in enumerate(counts)]


class CurrentPeriodListenCountTestCase(unittest.TestCase):
    """ Unit tests for the pure listening-activity current-period helper. """

    def test_week_sums_only_the_current_week(self):
        # Same data as user_listening_activity_db_data_for_api_test_week.json
        # (user 1): 14 daily segments, first 7 = previous week, last 7 = current.
        counts = [26, 57, 33, 40, 26, 17, 26, 32, 26, 28, 21, 26, 0, 4]
        records = _daily(datetime(2020, 4, 27), counts)  # Monday 27 April 2020

        count, from_ts = current_period_listen_count("week", records)

        self.assertEqual(count, 32 + 26 + 28 + 21 + 26 + 0 + 4)  # 137
        self.assertEqual(from_ts, _ts(datetime(2020, 5, 4)))  # Monday of current week

    def test_all_time_sums_every_segment(self):
        counts = [26, 57, 33, 40, 26, 17, 26, 32, 26, 28, 21, 26, 0, 4]
        records = _daily(datetime(2020, 4, 27), counts)

        count, from_ts = current_period_listen_count("all_time", records)

        self.assertEqual(count, sum(counts))  # 362
        self.assertEqual(from_ts, _ts(datetime(2020, 4, 27)))

    def test_month_split_handles_variable_month_lengths(self):
        # February 2021 (28 days) then March 2021 (31 days).
        records = _daily(datetime(2021, 2, 1), [1] * 28 + [10] * 31)

        count, from_ts = current_period_listen_count("month", records)

        self.assertEqual(count, 31 * 10)
        self.assertEqual(from_ts, _ts(datetime(2021, 3, 1)))

    def test_year_split_uses_monthly_segments(self):
        records = _monthly(datetime(2020, 1, 1), [1] * 12 + [5] * 12)

        count, from_ts = current_period_listen_count("year", records)

        self.assertEqual(count, 12 * 5)
        self.assertEqual(from_ts, _ts(datetime(2021, 1, 1)))

    def test_quarter_split_advances_three_months(self):
        prev_days = (datetime(2021, 10, 1) - datetime(2021, 7, 1)).days
        this_days = (datetime(2022, 1, 1) - datetime(2021, 10, 1)).days
        records = _daily(datetime(2021, 7, 1), [2] * prev_days + [3] * this_days)

        count, from_ts = current_period_listen_count("quarter", records)

        self.assertEqual(count, 3 * this_days)
        self.assertEqual(from_ts, _ts(datetime(2021, 10, 1)))

    def test_half_yearly_split_advances_six_months(self):
        records = _monthly(datetime(2021, 1, 1), [1] * 6 + [4] * 6)

        count, _ = current_period_listen_count("half_yearly", records)

        self.assertEqual(count, 6 * 4)

    def test_unordered_records_still_split_correctly(self):
        counts = [26, 57, 33, 40, 26, 17, 26, 32, 26, 28, 21, 26, 0, 4]
        records = _daily(datetime(2020, 4, 27), counts)
        records = list(reversed(records))

        count, _ = current_period_listen_count("week", records)

        self.assertEqual(count, 137)

    def test_empty_records(self):
        self.assertEqual(current_period_listen_count("week", []), (0, None))
