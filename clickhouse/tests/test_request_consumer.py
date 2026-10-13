import json
import unittest
from unittest import mock

from amqp.exceptions import PreconditionFailed

from clickhouse.request_consumer import ClickHouseRequestConsumer, RABBITMQ_MAX_MESSAGE_BYTES, serialize_result


class ClickHouseRequestConsumerTestCase(unittest.TestCase):

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

    def test_consume_acks_each_request_before_running_it(self):
        consumer = self._consumer_with_mock_broker()
        events = []
        message = mock.Mock(body=json.dumps({"query": "q"}))
        message.ack.side_effect = lambda: events.append("ack")
        bound_queue = mock.Mock()
        # one request, then an empty queue, then stop the loop
        bound_queue.get.side_effect = [message, None, KeyboardInterrupt]
        consumer.clickhouse_queue = mock.Mock(return_value=bound_queue)

        with mock.patch.object(consumer, "callback", side_effect=lambda body: events.append("run")), \
                mock.patch("clickhouse.request_consumer.time.sleep"):
            with self.assertRaises(KeyboardInterrupt):
                consumer.consume()

        self.assertEqual(events, ["ack", "run"])
        bound_queue.get.assert_called_with(no_ack=False)

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


    @mock.patch("clickhouse.request_consumer.RABBITMQ_MAX_MESSAGE_BYTES", 1000)
    def test_oversized_user_stats_message_is_split_by_users(self):
        users = [{"user_id": uid, "count": 1, "data": [{"time_range": "x" * 300}]} for uid in range(5)]
        message = {"type": "clk_user_entity", "entity": "listening_activity", "data": users}

        bodies = list(serialize_result(message))

        self.assertTrue(all(len(body) <= 1000 for body in bodies))
        parts = [json.loads(body) for body in bodies]
        self.assertEqual([u["user_id"] for part in parts for u in part["data"]], [0, 1, 2, 3, 4])
        self.assertTrue(all(part["entity"] == "listening_activity" for part in parts))

    @mock.patch("clickhouse.request_consumer.RABBITMQ_MAX_MESSAGE_BYTES", 1000)
    def test_oversized_single_user_is_dropped(self):
        big = {"user_id": 2, "count": 1, "data": [{"time_range": "x" * 2000}]}
        small = {"user_id": 1, "count": 1, "data": []}
        message = {"type": "clk_user_entity", "data": [small, big]}

        parts = [json.loads(body) for body in serialize_result(message)]

        self.assertEqual([[u["user_id"] for u in part["data"]] for part in parts], [[1]])
