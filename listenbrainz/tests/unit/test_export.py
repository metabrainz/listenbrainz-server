from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from listenbrainz.background.export import export_listens_for_user, get_time_ranges_for_listens


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

    @mock.patch('listenbrainz.background.export.update_export_progress')
    @mock.patch('listenbrainz.background.export.timescale_connection._ts')
    @mock.patch('listenbrainz.background.export.export_listens_for_time_range', return_value=1)
    def test_export_clamps_queries_to_user_history(self, export_range, store, update_progress):
        first = datetime(2022, 1, 15, tzinfo=timezone.utc)
        last = datetime(2022, 2, 10, tzinfo=timezone.utc)
        store.get_timestamps_for_user.return_value = (first, last)
        with TemporaryDirectory() as tmp_dir:
            files = export_listens_for_user(
                1, mock.Mock(), mock.Mock(), tmp_dir, 2,
                datetime(2000, 1, 1, tzinfo=timezone.utc),
                datetime(2030, 1, 1, tzinfo=timezone.utc),
            )
        self.assertEqual(len(files), 2)
        self.assertEqual(export_range.call_count, 2)
        self.assertEqual(export_range.call_args_list[0].args[3], first)
        self.assertEqual(export_range.call_args_list[-1].args[4], last)

    @mock.patch('listenbrainz.background.export.update_export_progress')
    @mock.patch('listenbrainz.background.export.timescale_connection._ts')
    @mock.patch('listenbrainz.background.export.export_listens_for_time_range')
    def test_export_skips_queries_when_range_does_not_overlap(self, export_range, store, update_progress):
        store.get_timestamps_for_user.return_value = (
            datetime(2022, 1, 15, tzinfo=timezone.utc),
            datetime(2022, 2, 10, tzinfo=timezone.utc),
        )
        with TemporaryDirectory() as tmp_dir:
            files = export_listens_for_user(
                1, mock.Mock(), mock.Mock(), tmp_dir, 2,
                datetime(2000, 1, 1, tzinfo=timezone.utc),
                datetime(2001, 1, 1, tzinfo=timezone.utc),
            )
        self.assertEqual(files, [])
        export_range.assert_not_called()
