from unittest.mock import patch, call

from listenbrainz_spark.tests import SparkTestCase
from listenbrainz_spark.stats.user.all import calculate


@patch('listenbrainz_spark.stats.user.entity.get_entity_week')
@patch('listenbrainz_spark.stats.user.entity.get_entity_month')
@patch('listenbrainz_spark.stats.user.entity.get_entity_year')
@patch('listenbrainz_spark.stats.user.entity.get_entity_all_time')
class UserStatsAllTestCase(SparkTestCase):
    def test_calculate(self, mock_get_entity_all_time, mock_get_entity_year,
                       mock_get_entity_month, mock_get_entity_week):
        calculate()

        calls = [call('artists'), call('releases'), call('recordings')]
        mock_get_entity_week.assert_has_calls(calls, any_order=True)
        mock_get_entity_month.assert_has_calls(calls, any_order=True)
        mock_get_entity_year.assert_has_calls(calls, any_order=True)
        mock_get_entity_all_time.assert_has_calls(calls, any_order=True)
