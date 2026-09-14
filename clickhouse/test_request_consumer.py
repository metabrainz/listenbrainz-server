import json
import unittest
from unittest import mock

from amqp.exceptions import PreconditionFailed

from clickhouse import config
from clickhouse.request_consumer import ClickHouseRequestConsumer, RABBITMQ_MAX_MESSAGE_BYTES


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

    def _consumer_with_mock_broker(self):
        consumer = ClickHouseRequestConsumer()
        consumer.connection = mock.Mock(
            connection_errors=(ConnectionError,),
            channel_errors=(PreconditionFailed,),
        )
        consumer.producer = mock.Mock()
        return consumer

    def test_callback_reraises_broker_errors_so_consumer_restarts(self):
        consumer = self._consumer_with_mock_broker()
        consumer.producer.publish.side_effect = PreconditionFailed("message too large")

        with mock.patch.object(consumer, "get_result", return_value=[{"type": "x"}]):
            with self.assertRaises(PreconditionFailed):
                consumer.callback(json.dumps({"query": "q"}))

    def test_callback_swallows_handler_errors(self):
        consumer = self._consumer_with_mock_broker()

        with mock.patch.object(consumer, "get_result", side_effect=ValueError("boom")):
            consumer.callback(json.dumps({"query": "q"}))

        consumer.producer.publish.assert_not_called()

    def test_push_to_result_queue_skips_oversized_messages(self):
        consumer = self._consumer_with_mock_broker()
        too_big = {"type": "clk_user_entity", "data": "x" * (RABBITMQ_MAX_MESSAGE_BYTES + 1)}

        count = consumer.push_to_result_queue([{"type": "a"}, too_big, {"type": "b"}])

        self.assertEqual(count, 2)
        published = [
            json.loads(call.kwargs["body"])["type"]
            for call in consumer.producer.publish.call_args_list
        ]
        self.assertEqual(published, ["a", "b"])


if __name__ == "__main__":
    unittest.main()
