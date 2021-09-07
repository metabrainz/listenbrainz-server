import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from listenbrainz_spark.stats.sitewide import entity
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats import (offset_days, offset_months,
                                      run_query, get_day_end, get_year_end, get_month_end)
from listenbrainz_spark.stats.user.tests import StatsTestCase


class SitewideEntityTestCase(StatsTestCase):

    @classmethod
    def setUpClass(cls):
        super(SitewideEntityTestCase, cls).setUpClass()
        entity.entity_handler_map['test'] = MagicMock(return_value="sample_test_data")

    @patch('listenbrainz_spark.stats.sitewide.entity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.sitewide.entity.create_message')
    def test_get_entity_week(self, mock_create_message, mock_get_listens):
        entity.get_entity_week('test')
        from_date = day = datetime(2021, 7, 26)
        to_date = datetime(2021, 8, 9)

        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%A %d %B %Y'), int(day.timestamp()), int(get_day_end(day).timestamp())])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_message.assert_called_with(data='sample_test_data', entity='test', stats_range='week',
                                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.sitewide.entity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.sitewide.entity.create_message')
    def test_get_entity_month(self, mock_create_message, mock_get_listens):
        entity.get_entity_month('test')
        from_date = datetime(2021, 7, 1)
        to_date = datetime(2021, 8, 9)
        day = from_date

        time_range = []
        while day < to_date:
            time_range.append([day.strftime('%d %B %Y'), int(day.timestamp()), int(get_day_end(day).timestamp())])
            day = offset_days(day, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_message.assert_called_with(data='sample_test_data', entity='test', stats_range='month',
                                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.sitewide.entity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.sitewide.entity.create_message')
    def test_get_entity_year(self, mock_create_message, mock_get_listens):
        entity.get_entity_year('test')
        from_date = datetime(2020, 1, 1)
        to_date = datetime(2021, 8, 9, 12, 22, 43)
        month = from_date

        time_range = []
        while month < to_date:
            time_range.append([month.strftime('%B %Y'), int(month.timestamp()), int(get_month_end(month).timestamp())])
            month = offset_months(month, 1, shift_backwards=False)
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_message.assert_called_with(data='sample_test_data', entity='test', stats_range='year',
                                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    @patch('listenbrainz_spark.stats.sitewide.entity.get_listens_from_new_dump')
    @patch('listenbrainz_spark.stats.sitewide.entity.create_message')
    def test_get_entity_all_time(self, mock_create_message, mock_get_listens):
        entity.get_entity_all_time('test')
        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
        to_date = datetime(2021, 8, 9, 12, 22, 43)

        time_range = [
            [str(year), int(datetime(year, 1, 1).timestamp()), int(get_year_end(year).timestamp())]
            for year in range(from_date.year, to_date.year + 1)
        ]
        time_range_df = run_query("SELECT * FROM time_range")
        time_range_result = time_range_df.rdd.map(list).collect()
        self.assertListEqual(time_range_result, time_range)

        mock_get_listens.assert_called_with(from_date, to_date)
        mock_create_message.assert_called_with(data='sample_test_data', entity='test', stats_range='all_time',
                                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    def test_create_message(self):
        """ Test to check if the number of entities are clipped to top 1000 """
        artists = []
        for i in range(0, 2000):
            artists.append({
                'artist_name': 'artist_{}'.format(i),
                'artist_mbids': [str(i)],
                'listen_count': i
            })

        mock_result = MagicMock()
        mock_result.asDict.return_value = {
            'time_range': "range",
            'artists': artists,
            'from_ts': 0,
            'to_ts': 1
        }

        message = entity.create_message([mock_result], 'artists', 'all_time', 0, 10)

        expected_list = artists[:1000]
        received_list = message[0]['data'][0]['artists']
        self.assertListEqual(received_list, expected_list)

    def test_skip_incorrect_artists_stats(self):
        """ Test to check if entries with incorrect data is skipped for top sitewide artists """
        with open(self.path_to_data_file('sitewide_top_artists_incorrect.json')) as f:
            data = json.load(f)

        mock_result = MagicMock()
        mock_result.asDict.return_value = data

        message = entity.create_message([mock_result], 'artists', 'all_time', 0, 10)
        received_list = message[0]['data'][0]['artists']

        # Only the first entry in file is valid, all others must be skipped
        self.assertListEqual(data['artists'][:1], received_list)
