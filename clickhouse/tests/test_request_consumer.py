import json
import socket
import unittest
import uuid
from unittest import mock

import orjson
from kombu import Connection, Exchange, Queue

from clickhouse import query_map
from clickhouse.request_consumer import ClickHouseRequestConsumer, PublishError, create_rabbitmq_connection


class StopConsumer(BaseException):
    """Raised by a test handler to stop consume(), which otherwise runs forever."""


def stop():
    raise StopConsumer()


def emit(types):
    for message_type in types:
        yield {"type": message_type}


def read_missing_dump():
    yield {"type": "a"}
    with open(f"/tmp/missing-dump-{uuid.uuid4().hex}"):
        pass


class ClickHouseRequestConsumerTestCase(unittest.TestCase):

    def setUp(self):
        self.consumer = ClickHouseRequestConsumer()
        # use exchanges and queues of our own, so the tests don't touch the real ones
        suffix = uuid.uuid4().hex
        self.consumer.clickhouse_exchange = Exchange(f"test_clickhouse_{suffix}", "fanout")
        self.consumer.clickhouse_queue = Queue(f"test_clickhouse_{suffix}", exchange=self.consumer.clickhouse_exchange)
        self.consumer.clickhouse_result_exchange = Exchange(f"test_clickhouse_result_{suffix}", "fanout")
        self.consumer.clickhouse_result_queue = Queue(
            f"test_clickhouse_result_{suffix}",
            exchange=self.consumer.clickhouse_result_exchange,
        )
        self.consumer.init_rabbitmq_connection()
        self.addCleanup(self.delete_broker_entities)
        self.addCleanup(lambda: self.consumer.connection.release())
        self.consumer.clickhouse_result_queue(self.consumer.connection.default_channel).declare()

        for name, handler in (("stop", stop), ("emit", emit), ("read_missing_dump", read_missing_dump)):
            query_map.functions[name] = handler
            self.addCleanup(query_map.functions.pop, name)
        capture_exception = mock.patch("clickhouse.request_consumer.sentry_sdk.capture_exception")
        self.capture_exception = capture_exception.start()
        self.addCleanup(capture_exception.stop)

    def delete_broker_entities(self):
        # on a fresh connection, as a test may have closed the consumer's channel
        with create_rabbitmq_connection("clickhouse-request-consumer-test") as connection:
            channel = connection.channel()
            for entity in (self.consumer.clickhouse_queue, self.consumer.clickhouse_exchange,
                           self.consumer.clickhouse_result_queue, self.consumer.clickhouse_result_exchange):
                entity(channel).delete()

    def send_requests(self, *requests):
        with create_rabbitmq_connection("clickhouse-request-consumer-test") as connection:
            self.consumer.clickhouse_queue(connection.default_channel).declare()
            for request in requests:
                connection.Producer().publish(
                    exchange=self.consumer.clickhouse_exchange,
                    routing_key="",
                    body=orjson.dumps(request),
                )

    def reported_exceptions(self) -> list[str]:
        """Names of the types of the exceptions reported to Sentry so far."""
        return [type(call.args[0]).__name__ for call in self.capture_exception.call_args_list]

    def get_results(self) -> list[dict]:
        queue = self.consumer.clickhouse_result_queue(self.consumer.connection.default_channel)
        results = []
        while (message := queue.get(no_ack=True)) is not None:
            results.append(json.loads(message.body))
        return results

    def test_consume_runs_requests_and_publishes_their_results(self):
        self.send_requests({"query": "emit", "params": {"types": ["a", "b"]}}, {"query": "stop"})

        with self.assertRaises(StopConsumer):
            self.consumer.consume()

        self.assertEqual(self.get_results(), [{"type": "a"}, {"type": "b"}])

    def test_results_are_kept_until_the_reader_consumes_them(self):
        self.consumer.clickhouse_result_queue(self.consumer.connection.default_channel).delete()
        self.send_requests({"query": "emit", "params": {"types": ["a"]}}, {"query": "stop"})

        with self.assertRaises(StopConsumer):
            self.consumer.consume()

        self.assertEqual(self.get_results(), [{"type": "a"}])

    def test_consume_acks_each_request_before_running_it(self):
        self.send_requests({"query": "stop"})

        with self.assertRaises(StopConsumer):
            self.consumer.consume()
        self.consumer.connection.release()

        self.consumer.init_rabbitmq_connection()
        queue = self.consumer.clickhouse_queue(self.consumer.connection.default_channel)
        _, message_count, _ = queue.queue_declare(passive=True)
        self.assertEqual(message_count, 0)

    def test_message_rejected_by_the_broker_is_dropped(self):
        channel = self.consumer.connection.default_channel
        self.consumer.clickhouse_result_exchange(channel).delete()

        self.assertEqual(self.consumer.push_to_result_queue([{"type": "a"}]), 0)
        self.assertEqual(self.reported_exceptions(), ["NotFound"])

        # the producer moved to a new channel, and the request queue's channel is still open
        self.consumer.clickhouse_result_queue(channel).declare()
        self.assertEqual(self.consumer.push_to_result_queue([{"type": "b"}]), 1)
        self.assertEqual(self.get_results(), [{"type": "b"}])

    def test_publish_reconnects_after_a_broker_error(self):
        self.consumer.connection.connection.transport.sock.shutdown(socket.SHUT_RDWR)

        self.consumer.publish(orjson.dumps({"type": "a"}))

        self.assertEqual(self.get_results(), [{"type": "a"}])

    def test_callback_reraises_publish_errors_so_consumer_restarts(self):
        self.consumer.connection.release()
        self.consumer.connection = Connection(
            "amqp://guest:guest@rabbitmq:1//",
            transport_options={"confirm_publish": True},
        )
        self.consumer.producer = self.consumer.connection.Producer(channel=self.consumer.connection)
        self.consumer.publish_retry_policy = {"max_retries": 1, "interval_start": 0, "interval_step": 0}

        with self.assertRaises(PublishError):
            self.consumer.callback(json.dumps({"query": "emit", "params": {"types": ["a"]}}))
        self.assertEqual(self.reported_exceptions(), ["PublishError"])

    def test_callback_reports_and_swallows_handler_errors(self):
        for request in ({"query": "emit", "params": {"unknown": 1}}, {"query": "read_missing_dump"}):
            with self.subTest(request=request):
                self.consumer.callback(json.dumps(request))

        self.assertEqual(self.reported_exceptions(), ["TypeError", "FileNotFoundError"])
        self.assertEqual(self.get_results(), [{"type": "a"}])

    def test_unserializable_message_is_skipped(self):
        messages = [{"type": "a"}, {"type": "b", "data": 2 ** 64}, {"type": "c", "data": {1: 2}}]

        count = self.consumer.push_to_result_queue(messages)

        self.assertEqual(count, 2)
        self.assertEqual(self.get_results(), [{"type": "a"}, {"type": "c", "data": {"1": 2}}])
        self.assertEqual(self.reported_exceptions(), ["TypeError"])
