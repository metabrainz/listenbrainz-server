import socket
import uuid
from unittest import mock

import orjson
from kombu import Connection
from sqlalchemy import text

from listenbrainz.clickhouse import jobs, queues
from listenbrainz.clickhouse.query_worker import query_map, worker
from listenbrainz.clickhouse.query_worker.worker import ClickHouseQueryWorker

from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app, db_conn
from listenbrainz.webserver.testing import ServerTestCase


class StopConsumer(BaseException):
    """Raised by a test handler to stop do_run(), which otherwise runs forever."""


def stop():
    raise StopConsumer()


def emit(types):
    for message_type in types:
        yield {"type": message_type}


def read_missing_dump():
    yield {"type": "a"}
    with open(f"/tmp/missing-dump-{uuid.uuid4().hex}"):
        pass


class ClickHouseQueryWorkerTestCase(ServerTestCase):

    @classmethod
    def create_app(cls):
        app = create_app()
        app.config["TESTING"] = True
        return app

    def setUp(self):
        super().setUp()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db_conn.execute(text("DELETE FROM clickhouse_query_jobs"))
        db_conn.commit()

        # use exchanges and queues of our own, so the tests don't touch the real ones
        suffix = uuid.uuid4().hex
        self.app.config["CLICKHOUSE_RESULT_EXCHANGE"] = f"test_clickhouse_result_{suffix}"
        self.app.config["CLICKHOUSE_RESULT_QUEUE"] = f"test_clickhouse_result_{suffix}"
        queues.init_queues(self.app.config)

        self.consumer = ClickHouseQueryWorker()
        self.consumer.init_rabbitmq_connection()
        self.addCleanup(self.delete_broker_entities)
        self.addCleanup(lambda: self.consumer.connection.release())
        self.addCleanup(self.consumer.reset_producer)

        for name, handler in (("stop", stop), ("emit", emit), ("read_missing_dump", read_missing_dump)):
            query_map.functions[name] = handler
            self.addCleanup(query_map.functions.pop, name)

    def tearDown(self):
        db_conn.rollback()
        db_conn.execute(text("DELETE FROM clickhouse_query_jobs"))
        db_conn.commit()
        self.ctx.pop()
        super().tearDown()

    def delete_broker_entities(self):
        # on a fresh connection, as a test may have closed the consumer's channel
        with create_rabbitmq_connection(
            self.app.config,
            "clickhouse-query-worker-test",
            transport_options={"confirm_publish": True}
        ) as connection:
            channel = connection.channel()
            for entity in (
                queues.CLICKHOUSE_RESULT_QUEUE,
                queues.CLICKHOUSE_RESULT_EXCHANGE
            ):
                entity(channel).delete()

    def send_requests(self, *requests):
        for request in requests:
            jobs.add_job(request["query"], request.get("params", {}))

    def reported_exceptions(self, capture_exception) -> list[str]:
        """Names of the types of the exceptions reported to Sentry so far."""
        return [type(call.args[0]).__name__ for call in capture_exception.call_args_list]

    def get_results(self) -> list[dict]:
        queue = queues.CLICKHOUSE_RESULT_QUEUE(self.consumer.connection.default_channel)
        results = []
        while (message := queue.get(no_ack=True)) is not None:
            results.append(orjson.loads(message.body))
        return results

    def test_consume_runs_requests_and_publishes_their_results(self):
        self.send_requests(
            {"query": "emit", "params": {"types": ["a", "b"]}},
            {"query": "stop"}
        )

        with self.assertRaises(StopConsumer):
            self.consumer.do_run()

        self.assertEqual(self.get_results(), [{"type": "a"}, {"type": "b"}])

    def test_results_are_kept_until_the_reader_consumes_them(self):
        queues.CLICKHOUSE_RESULT_QUEUE(self.consumer.connection.default_channel).delete()
        self.send_requests({"query": "emit", "params": {"types": ["a"]}}, {"query": "stop"})

        with self.assertRaises(StopConsumer):
            self.consumer.do_run()

        self.assertEqual(self.get_results(), [{"type": "a"}])

    @mock.patch("listenbrainz.clickhouse.query_worker.worker.sentry_sdk.capture_exception")
    def test_message_rejected_by_the_broker_is_dropped(self, capture_exception):
        # the first publish declares the result queue, later ones on this connection don't
        self.assertEqual(self.consumer.push_to_result_queue([{"type": "a"}]), 1)
        channel = self.consumer.connection.default_channel
        queues.CLICKHOUSE_RESULT_EXCHANGE(channel).delete()

        self.assertEqual(self.consumer.push_to_result_queue([{"type": "b"}]), 0)
        self.assertEqual(self.reported_exceptions(capture_exception), ["NotFound"])

        # the producer moved to a new connection, which declares the result queue again
        self.assertEqual(self.consumer.push_to_result_queue([{"type": "c"}]), 1)
        self.assertEqual(self.get_results(), [{"type": "a"}, {"type": "c"}])

    def test_publish_reconnects_after_a_broker_error(self):
        self.consumer.producer_connection.connection.transport.sock.shutdown(socket.SHUT_RDWR)

        self.consumer.publish(orjson.dumps({"type": "a"}))

        self.assertEqual(self.get_results(), [{"type": "a"}])

    @mock.patch.object(worker.time, "sleep", side_effect=StopConsumer)
    def test_handler_failure_marks_job_failed_and_processes_next_job(self, sleep):
        self.send_requests(
            {"query": "read_missing_dump"},
            {"query": "emit", "params": {"types": ["b"]}},
        )
        with self.assertRaises(StopConsumer):
            self.consumer.do_run()
        self.assertIsNone(jobs.claim_job())
        failed = db_conn.execute(text("SELECT * FROM clickhouse_query_jobs")).one()
        self.assertEqual(failed.query, "read_missing_dump")
        self.assertIsNotNone(failed.failed_at)
        # Even an expired or released claim must not resurrect a failed job.
        db_conn.execute(text("UPDATE clickhouse_query_jobs SET claimed_at = now() - interval '7 hours'"))
        db_conn.commit()
        self.assertIsNone(jobs.claim_job())
        db_conn.execute(text("UPDATE clickhouse_query_jobs SET claimed_at = NULL"))
        db_conn.commit()
        self.assertIsNone(jobs.claim_job())
        self.assertEqual(self.get_results(), [{"type": "a"}, {"type": "b"}])

    def test_claims_survive_commits_and_expire(self):
        self.send_requests({"query": "emit", "params": {"types": []}})
        first = jobs.claim_job()
        db_conn.commit()
        self.assertIsNone(jobs.claim_job())
        db_conn.execute(text("UPDATE clickhouse_query_jobs SET claimed_at = now() - interval '7 hours'"))
        db_conn.commit()
        reclaimed = jobs.claim_job()
        self.assertEqual(reclaimed.id, first.id)
        jobs.remove_job(first)
        jobs.release_job(first)
        jobs.fail_job(first)
        self.assertIsNone(jobs.claim_job())
        jobs.release_job(reclaimed)
        self.assertEqual(jobs.claim_job().id, first.id)

    @mock.patch.object(worker.time, "sleep", side_effect=StopConsumer)
    def test_success_removes_job(self, sleep):
        self.send_requests({"query": "emit", "params": {"types": ["a"]}})
        with self.assertRaises(StopConsumer):
            self.consumer.do_run()
        self.assertIsNone(jobs.claim_job())
        self.assertEqual(self.get_results(), [{"type": "a"}])

    def test_shutdown_releases_job(self):
        self.send_requests({"query": "emit"})
        self.consumer._current_job = jobs.claim_job()
        with self.assertRaises(SystemExit):
            self.consumer._release_on_shutdown(None, None)
        self.assertEqual(jobs.claim_job().id, self.consumer._current_job.id)

    @mock.patch("listenbrainz.clickhouse.query_worker.worker.sentry_sdk.capture_exception")
    def test_unserializable_message_is_skipped(self, capture_exception):
        messages = [{"type": "a"}, {"type": "b", "data": 2 ** 64}, {"type": "c", "data": {1: 2}}]

        count = self.consumer.push_to_result_queue(messages)

        self.assertEqual(count, 2)
        self.assertEqual(self.get_results(), [{"type": "a"}, {"type": "c", "data": {"1": 2}}])
        self.assertEqual(self.reported_exceptions(capture_exception), ["TypeError"])
