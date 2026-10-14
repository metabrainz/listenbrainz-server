import threading

from listenbrainz.clickhouse.result_consumer.testing import ClickHouseResultConsumerTestCase


class ClickHouseResultConsumerCallbackTestCase(ClickHouseResultConsumerTestCase):

    def test_dispatches_message_to_handler(self):
        message = {"type": "clk_test", "data": [{"user_id": 1, "count": 5}]}
        received = []

        def handler(response):
            received.append(response)
            self.reader.should_stop = True

        self.register_handler("clk_test", handler)
        self.publish_result(message)

        # stop the consumer even if the handler is never called
        timer = threading.Timer(10, setattr, (self.reader, "should_stop", True))
        timer.start()
        self.addCleanup(timer.cancel)
        self.reader.init_rabbitmq_connection()
        self.addCleanup(self.reader.connection.release)
        self.reader.run()

        self.assertEqual(received, [message])
        self.assertEqual(self.queued_result_count(), 0)
