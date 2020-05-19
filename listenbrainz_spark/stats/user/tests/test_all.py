from unittest.mock import patch

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.stats.user.all import calculate


@patch('listenbrainz_spark.stats.user.artist.get_artists_week')
@patch('listenbrainz_spark.stats.user.artist.get_artists_month')
@patch('listenbrainz_spark.stats.user.artist.get_artists_last_year')
@patch('listenbrainz_spark.stats.user.artist.get_artists_all_time')
class UserStatsAllTestCase(SparkTestCase):
    def test_calculate(self, mock_get_artists_all_time, mock_get_artists_last_year,
                       mock_get_artists_month, mock_get_artists_week):
        calculate()

        mock_get_artists_week.assert_called_once()
        mock_get_artists_month.assert_called_once()
        mock_get_artists_last_year.assert_called_once()
        mock_get_artists_all_time.assert_called_once()
