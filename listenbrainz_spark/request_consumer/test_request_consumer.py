from unittest.mock import patch, MagicMock

from listenbrainz_spark.request_consumer.request_consumer import RequestConsumer
from listenbrainz_spark.tests import SparkNewTestCase


class RequestConsumerTestCase(SparkNewTestCase):

    def setUp(self):
        self.consumer = RequestConsumer()
        self.consumer.rabbitmq = MagicMock()
        self.consumer.request_channel = MagicMock()
        self.consumer.result_channel = MagicMock()

    def test_get_result_if_bad_query(self):
        # should return none if no query
        self.assertIsNone(self.consumer.get_result({}))

        # should return none if unrecognized query
        self.assertIsNone(self.consumer.get_result({'query': 'idk_what_this_means'}))

    @patch('listenbrainz_spark.query_map.get_query_handler')
    def test_get_result_if_query_recognized(self, mock_get_query_handler):
        # should call the returned function if query is recognized
        # create the mock query handler
        mock_query_handler = MagicMock()
        mock_query_handler.return_value = {'result': 'ok'}

        # make the get_query_handler function return the mock query handler
        mock_get_query_handler.return_value = mock_query_handler

        # assert that we get the correct result
        self.assertEqual(self.consumer.get_result({'query': 'i_know_what_this_means'}), {'result': 'ok'})
        mock_get_query_handler.assert_called_once()
        mock_query_handler.assert_called_once()
