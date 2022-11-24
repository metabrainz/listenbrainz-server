import calendar
import itertools
import json
from datetime import datetime
from unittest.mock import patch

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats.user import daily_activity
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.user.tests import StatsTestCase


class DailyActivityTestCase(StatsTestCase):

    def test_get_daily_activity(self):
        messages = list(daily_activity.get_daily_activity('all_time'))

        time_range_expected = itertools.product(calendar.day_name, range(0, 24))
        time_range_received = run_query("SELECT * FROM time_range").toLocalIterator()
        self.assertListEqual(list(time_range_expected), list(time_range_received))

        with open(self.path_to_data_file('user_daily_activity.json')) as f:
            expected = json.load(f)

        self.assertEqual(messages[0]["type"], "couchdb_data_start")
        self.assertEqual(messages[0]["database"], "daily_activity_all_time")

        self.assertEqual(messages[1]["type"], expected[0]["type"])
        self.assertEqual(messages[1]["stats_range"], expected[0]["stats_range"])
        self.assertEqual(messages[1]["from_ts"], expected[0]["from_ts"])
        self.assertEqual(messages[1]["to_ts"], expected[0]["to_ts"])
        self.assertCountEqual(messages[1]["data"], expected[0]["data"])
        self.assertCountEqual(messages[1]["database"], "daily_activity_all_time")

        self.assertEqual(messages[2]["type"], "couchdb_data_end")
        self.assertEqual(messages[2]["database"], "daily_activity_all_time")

    @patch('listenbrainz_spark.stats.user.daily_activity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.daily_activity.calculate_daily_activity', return_value='daily_activity_table')
    @patch('listenbrainz_spark.stats.user.daily_activity.create_messages')
    def test_get_daily_activity_week(self, mock_create_messages, _, mock_get_listens):
        daily_activity.get_daily_activity('week')

        from_date = datetime(2021, 8, 2)
        to_date = datetime(2021, 8, 9)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='daily_activity_table', stats_range='week',
                                                from_date=from_date, to_date=to_date, database=None)

    @patch('listenbrainz_spark.stats.user.daily_activity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.daily_activity.calculate_daily_activity', return_value='daily_activity_table')
    @patch('listenbrainz_spark.stats.user.daily_activity.create_messages')
    def test_get_daily_activity_month(self, mock_create_messages, _, mock_get_listens):
        daily_activity.get_daily_activity('month')

        from_date = datetime(2021, 7, 1)
        to_date = datetime(2021, 8, 1)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='daily_activity_table', stats_range='month',
                                                from_date=from_date, to_date=to_date, database=None)

    @patch('listenbrainz_spark.stats.user.daily_activity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.daily_activity.calculate_daily_activity', return_value='daily_activity_table')
    @patch('listenbrainz_spark.stats.user.daily_activity.create_messages')
    def test_get_daily_activity_year(self, mock_create_messages, _, mock_get_listens):
        daily_activity.get_daily_activity('year')

        from_date = datetime(2020, 1, 1)
        to_date = datetime(2021, 1, 1)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='daily_activity_table', stats_range='year',
                                                from_date=from_date, to_date=to_date, database=None)

    @patch('listenbrainz_spark.stats.user.daily_activity.get_listens_from_dump')
    @patch('listenbrainz_spark.stats.user.daily_activity.calculate_daily_activity', return_value='daily_activity_table')
    @patch('listenbrainz_spark.stats.user.daily_activity.create_messages')
    def test_get_daily_activity_all_time(self, mock_create_messages, _, mock_get_listens):
        daily_activity.get_daily_activity('all_time')

        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = datetime(2021, 8, 9, 12, 22, 43)
        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='daily_activity_table', stats_range='all_time',
                                                from_date=from_date, to_date=to_date, database=None)
