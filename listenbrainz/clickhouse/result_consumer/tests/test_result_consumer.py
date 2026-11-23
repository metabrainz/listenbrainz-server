import threading
from unittest.mock import patch

import requests

from listenbrainz.clickhouse.result_consumer.testing import ClickHouseResultConsumerTestCase


class ClickHouseResultConsumerCallbackTestCase(ClickHouseResultConsumerTestCase):

    def test_transient_failure_requeues_batch(self):
        batch = {"type": "clk_daily_activity", "database": "daily_test", "from_ts": 0, "to_ts": 1, "data": []}
        self.publish_result(batch)
        message = self.result_queue.get()
        with patch("listenbrainz.clickhouse.result_consumer.handlers.stats.insert",
                   side_effect=requests.Timeout) as insert:
            self.reader.callback(message)
        insert.assert_called_once()
        redelivered = self.result_queue.get()
        self.assertIsNotNone(redelivered)
        self.assertTrue(redelivered.delivery_info["redelivered"])
        self.assertEqual(redelivered.body, message.body)
        with patch("listenbrainz.clickhouse.result_consumer.handlers.stats.insert") as insert:
            self.reader.callback(redelivered)
        insert.assert_called_once()
        self.assertEqual(self.queued_result_count(), 0)

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
