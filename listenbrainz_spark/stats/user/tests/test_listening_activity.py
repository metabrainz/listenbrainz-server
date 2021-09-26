import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import listenbrainz_spark.stats.user.listening_activity as listening_activity_stats
from listenbrainz_spark import utils
from listenbrainz_spark.exceptions import HDFSException
from listenbrainz_spark.stats import (offset_days, offset_months, get_day_end,
                                      get_month_end, run_query)
from listenbrainz_spark.stats.user.tests import StatsTestCase
from pyspark.sql import Row


def _mock_get_listens_all_time(from_date: datetime, to_date: datetime):
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../..', 'testdata')
    file_ = os.path.join(path, 'user_listening_activity_all_time.json')
    with open(file_) as f:
        data = json.load(f)

    listens_df = None
    for entry in data:
        if entry['year'] == from_date.year:
            row = utils.create_dataframe(Row(user_name=entry['user_name'], listened_at=from_date), schema=None)
            listens_df = listens_df.union(row) if listens_df else row

    if listens_df is None:
        raise HDFSException('')

    listens_df.createOrReplaceTempView('listens')


class ListeningActivityTestCase(StatsTestCase):

    def test_get_listening_activity(self):
        with open(self.path_to_data_file('user_listening_activity.json')) as f:
            expected = json.load(f)
        received = listening_activity_stats.get_listening_activity_all_time()
        self.assertCountEqual(expected, list(received))

    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_week(self, mock_create_messages, _, mock_get_listens):
        listening_activity_stats.get_listening_activity_week()

        from_date = day = datetime(2021, 7, 26)
        to_date = datetime(2021, 8, 2)
        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%A %d %B %Y'), day, get_day_end(day)])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='activity_table', stats_range='week',
                                                from_date=from_date, to_date=to_date)

    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_month(self, mock_create_messages, _, mock_get_listens):
        listening_activity_stats.get_listening_activity_month()

        from_date = day = datetime(2021, 7, 1)
        to_date = datetime(2021, 8, 1)
        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%d %B %Y'), day, get_day_end(day)])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='activity_table', stats_range='month',
                                                from_date=from_date, to_date=to_date)

    @patch('listenbrainz_spark.stats.user.listening_activity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.user.listening_activity.get_listening_activity', return_value='activity_table')
    @patch('listenbrainz_spark.stats.user.listening_activity.create_messages')
    def test_get_listening_activity_year(self, mock_create_messages, _, mock_get_listens):
        listening_activity_stats.get_listening_activity_year()

        from_date = month = datetime(2020, 1, 1)
        to_date = datetime(2021, 1, 1)
        time_range = []
        while month < to_date:
            time_range.append([month.strftime('%B %Y'), month, get_month_end(month)])
            month = offset_months(month, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_messages.assert_called_with(data='activity_table', stats_range='year',
                                                from_date=from_date, to_date=to_date)
