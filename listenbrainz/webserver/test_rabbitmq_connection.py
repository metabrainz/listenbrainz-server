from unittest import TestCase
from unittest.mock import patch, MagicMock
from pika.exceptions import ConnectionClosed


from listenbrainz.webserver.rabbitmq_connection import RabbitMQConnectionPool, CONNECTION_RETRIES


class RabbitMQConnectionPoolTestCase(TestCase):

    def setUp(self):
        self.pool = RabbitMQConnectionPool(MagicMock(), MagicMock(), 10)

    @patch('listenbrainz.webserver.rabbitmq_connection.pika.BlockingConnection')
    @patch('listenbrainz.webserver.rabbitmq_connection.sleep')
    def test_connection_closed_while_creating(self, mock_sleep, mock_blocking_connection):
        mock_blocking_connection.side_effect = ConnectionClosed
        with self.assertRaises(ConnectionClosed):
            connection = self.pool.create()
            self.pool.log.critical.assert_called_once()
            self.assertEqual(self.mock_sleep.call_count, CONNECTION_RETRIES - 1)
