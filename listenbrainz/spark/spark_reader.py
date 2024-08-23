#!/usr/bin/env python3
import time

from redis.client import Redis

from listenbrainz.spark.background import BackgroundJobProcessor
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app

PREFETCH_COUNT = 1000


class SparkReader:

    def __init__(self, app):
        self.app = app
        self.redis_conn: Redis | None = None
        self.processor: BackgroundJobProcessor | None = None
        self.last_seen_id = b"0-0"

    def run(self):
        while True:
            streams = self.redis_conn.xread(
                {self.app.config["SPARK_RESULT_STREAM"]: self.last_seen_id},
                count=PREFETCH_COUNT,
                block=5000
            )
            if not streams:
                continue

            self.app.logger.info('Received a request!')
            messages = streams[0][1]
            message_id, body = messages[0]
            with self.app.app_context():
                self.processor.process_message(body)

            self.last_seen_id = message_id
            self.redis_conn.xtrim(self.app.config["SPARK_RESULT_STREAM"], minid=self.last_seen_id)
            self.redis_conn.set(self.app.config["SPARK_RESULT_STREAM_LAST_SEEN"], self.last_seen_id)
            self.app.logger.info('Request done!')

    def init_redis_connection(self):
        self.redis_conn = Redis(
            self.app.config["REDIS_HOST"],
            self.app.config["REDIS_PORT"],
            client_name=get_fallback_connection_name()
        )
        self.last_seen_id = self.redis_conn.get(self.app.config["SPARK_RESULT_STREAM_LAST_SEEN"]) or b"0-0"

    def start(self):
        """ initiates RabbitMQ connection and starts consuming from the queue """
        while True:
            try:
                self.app.logger.info("Spark consumer has started!")
                self.init_redis_connection()
                self.processor = BackgroundJobProcessor(self.app)
                self.run()
            except KeyboardInterrupt:
                self.app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                self.app.logger.error("Error in SparkReader:", exc_info=True)
                time.sleep(3)


if __name__ == '__main__':
    sr = SparkReader(create_app())
    sr.start()
