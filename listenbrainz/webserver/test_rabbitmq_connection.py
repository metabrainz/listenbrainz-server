from flask import Flask
from unittest import TestCase
from unittest.mock import patch, MagicMock
from pika.exceptions import ConnectionClosed

import listenbrainz.webserver.rabbitmq_connection as rabbitmq_connection

from listenbrainz.webserver.rabbitmq_connection import RabbitMQConnectionPool, CONNECTION_RETRIES, init_rabbitmq_connection



class RabbitMQConnectionPoolTestCase(TestCase):

    def setUp(self):
        self.pool = RabbitMQConnectionPool(MagicMock(), MagicMock(), 10, 'test_exchange')

    @patch('listenbrainz.webserver.rabbitmq_connection.pika.BlockingConnection')
    @patch('listenbrainz.webserver.rabbitmq_connection.sleep')
    def test_connection_closed_while_creating(self, mock_sleep, mock_blocking_connection):
        mock_blocking_connection.side_effect = ConnectionClosed
        with self.assertRaises(ConnectionClosed):
            connection = self.pool.create()
            self.pool.log.critical.assert_called_once()
            self.assertEqual(self.mock_sleep.call_count, CONNECTION_RETRIES - 1)

    def test_connection_error_when_rabbitmq_down(self):
        # create an app with no RabbitMQ config
        # as will be the case when RabbitMQ is down in production
        app = Flask(__name__)

        with self.assertRaises(ConnectionError):
            rabbitmq_connection._rabbitmq = None
            init_rabbitmq_connection(app)
