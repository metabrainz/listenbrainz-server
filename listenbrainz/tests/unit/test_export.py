from datetime import datetime, timezone
from unittest import TestCase

from listenbrainz.background.export import get_time_ranges_for_listens


class ExportTimeRangesTestCase(TestCase):
    def test_partial_months_across_year_boundary(self):
        start = datetime(2023, 12, 20, 12, 30, tzinfo=timezone.utc)
        end = datetime(2024, 3, 10, 18, 45, tzinfo=timezone.utc)
        ranges = get_time_ranges_for_listens(start, end)
        months = [month for year in ranges for month in year['months']]
        self.assertEqual([year['year'] for year in ranges], [2023, 2024])
        self.assertEqual([month['month'] for month in months], [12, 1, 2, 3])
        self.assertEqual(months[0]['start'], start)
        self.assertEqual(months[-1]['end'], end)
        self.assertEqual(months[2]['end'], datetime(2024, 2, 29, 23, 59, 59, 999999, tzinfo=timezone.utc))

    def test_empty_range_within_one_month(self):
        self.assertEqual(get_time_ranges_for_listens(
            datetime(2024, 1, 20, tzinfo=timezone.utc),
            datetime(2024, 1, 10, tzinfo=timezone.utc),
        ), [])
