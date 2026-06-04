import unittest
from unittest import mock

from clickhouse import config
from clickhouse.request_consumer import ClickHouseRequestConsumer


class ClickHouseRequestConsumerTestCase(unittest.TestCase):

    @mock.patch("clickhouse.request_consumer.socket.gethostname", return_value="test-host")
    @mock.patch("clickhouse.request_consumer.Connection")
    def test_init_rabbitmq_connection_uses_rabbitmq_hosts(
        self,
        mock_connection_class,
        _mock_hostname,
    ):
        connection = mock.Mock()
        mock_connection_class.return_value = connection

        with mock.patch.multiple(
            config,
            RABBITMQ_HOSTS=[("rabbitmq-1", 5672), ("rabbitmq-2", 5672)],
            RABBITMQ_USERNAME="listenbrainz",
            RABBITMQ_PASSWORD="secret",
            RABBITMQ_VHOST="/listenbrainz",
        ):
            consumer = ClickHouseRequestConsumer()
            consumer.init_rabbitmq_connection()

        mock_connection_class.assert_called_once_with(
            hostname=[
                "amqp://listenbrainz:secret@rabbitmq-1:5672//listenbrainz",
                "amqp://listenbrainz:secret@rabbitmq-2:5672//listenbrainz",
            ],
            transport_options={
                "client_properties": {
                    "connection_name": "clickhouse-request-consumer-test-host",
                },
            },
        )
        self.assertEqual(consumer.connection, connection)
        self.assertEqual(consumer.producer, connection.Producer.return_value)


if __name__ == "__main__":
    unittest.main()
