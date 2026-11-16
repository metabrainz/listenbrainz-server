#!/usr/bin/env python3
"""Run persistent ClickHouse query jobs and publish results to RabbitMQ."""

import signal
import socket
import time
from collections.abc import Iterable

import orjson
import sentry_sdk
from amqp.exceptions import ChannelError, MessageNacked
from flask import current_app
from kombu.entity import PERSISTENT_DELIVERY_MODE
from kombu.mixins import ConsumerProducerMixin

from listenbrainz.clickhouse import jobs, queues
from listenbrainz.clickhouse.query_worker import query_map
from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app, db_conn


PUBLISH_TIMEOUT = 60
PUBLISH_RETRY_POLICY = {
    "max_retries": 10,
    "interval_start": 1,
    "interval_step": 5,
    "interval_max": 30,
}


class ClickHouseQueryWorker(ConsumerProducerMixin):
    """Claim jobs durably and retry interrupted queries.

    Handler failures are terminal. Interrupted queries may republish earlier results. Claims expire after six hours,
    matching background tasks; jobs should finish within that window.
    """

    def __init__(self):
        self._current_job = None
        self.connection = None
        self.publish_retry_policy = PUBLISH_RETRY_POLICY

    def get_result(self, query: str, params: dict) -> Iterable[dict] | None:
        """Process a query and return the result."""
        current_app.logger.info('Query: %s, params: %s', query, params)

        query_handler = query_map.functions.get(query)
        if query_handler is None:
            current_app.logger.error("Unknown query: %s", query)
            return None

        return query_handler(**params)

    def publish(self, body: bytes) -> bool:
        """Publish with retries and return whether the broker accepted the result.

        Drop rejected results and replace the channel if the broker closed it.
        """
        try:
            self.producer.publish(
                exchange=queues.CLICKHOUSE_RESULT_EXCHANGE,
                routing_key="",
                body=body,
                declare=[queues.CLICKHOUSE_RESULT_QUEUE],
                delivery_mode=PERSISTENT_DELIVERY_MODE,
                timeout=PUBLISH_TIMEOUT,
                retry=True,
                retry_policy=self.publish_retry_policy,
            )
            return True
        except (ChannelError, MessageNacked) as e:
            current_app.logger.error(
                "RabbitMQ rejected a ClickHouse result message of %d bytes, dropping it: %s",
                len(body),
                str(e),
                exc_info=True
            )
            sentry_sdk.capture_exception(e)
            if isinstance(e, ChannelError):
                self.reset_producer()
            return False

    def reset_producer(self):
        """Close the producer connection, as the broker closed its channel; the next publish opens a new one."""
        if self._producer_connection is not None:
            self._producer_connection.close()
            self._producer_connection = None

    def push_to_result_queue(self, messages: Iterable[dict]) -> int:
        """Publish results, skipping unserializable or rejected messages.

        Handler errors and PublishErrors propagate.
        """
        if not messages:
            return 0

        message_count = 0
        total_size = 0
        for message in messages:
            try:
                body = orjson.dumps(message, option=orjson.OPT_NON_STR_KEYS)
            except TypeError as e:
                current_app.logger.error(
                    "Skipping ClickHouse result message of type %s that cannot be serialized: %s",
                    message.get("type"),
                    str(e),
                    exc_info=True
                )
                sentry_sdk.capture_exception(e)
                continue
            if self.publish(body):
                total_size += len(body)
                message_count += 1
        if message_count:
            current_app.logger.info(
                "Pushed %d ClickHouse result messages, average size %d bytes",
                message_count,
                total_size // message_count,
            )
        else:
            current_app.logger.info("No ClickHouse result messages generated")
        return message_count

    def process_job(self, job):
        results = self.get_result(job.query, job.params)
        if results:
            self.push_to_result_queue(results)

    def _release_on_shutdown(self, signum, frame):
        if self._current_job is not None:
            try:
                db_conn.rollback()
                jobs.release_job(self._current_job)
            except Exception:
                current_app.logger.exception("Failed to release query job on shutdown")
        raise SystemExit(0)

    def do_run(self):
        while True:
            job = jobs.claim_job()
            if job is None:
                time.sleep(current_app.config.get("CLICKHOUSE_QUERY_WORKER_SLEEP_TIME", 5))
                continue
            self._current_job = job
            try:
                self.process_job(job)
                jobs.remove_job(job)
            except Exception:
                current_app.logger.exception("Error processing ClickHouse query job %s", job.id)
                db_conn.rollback()
                jobs.fail_job(job)
            finally:
                self._current_job = None
                db_conn.rollback()

    def init_rabbitmq_connection(self):
        """Initialize RabbitMQ connection."""
        connection_name = "clickhouse-query-worker-" + socket.gethostname()
        self.connection = create_rabbitmq_connection(
            current_app.config, connection_name, transport_options={"confirm_publish": True}
        )

    def start(self):
        """Start the worker, letting failures exit so the service can restart."""
        try:
            current_app.logger.info("ClickHouse query worker starting...")
            signal.signal(signal.SIGTERM, self._release_on_shutdown)
            self.init_rabbitmq_connection()
            self.do_run()
        except Exception as e:
            current_app.logger.critical("Error in ClickHouse query worker: %s", str(e), exc_info=True)
            raise
        finally:
            self.reset_producer()
            if self.connection is not None:
                self.connection.release()


def main():
    """Entry point for the worker."""
    with create_app().app_context():
        queues.init_queues(current_app.config)
        worker = ClickHouseQueryWorker()
        worker.start()


if __name__ == '__main__':
    main()
