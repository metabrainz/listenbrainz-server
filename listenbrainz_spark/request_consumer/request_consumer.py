# listenbrainz-labs
#
# Copyright (C) 2019 Param Singh <iliekcomputers@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import json
import socket
import time
import logging

import orjson
from redis.client import Redis

import listenbrainz_spark
import listenbrainz_spark.query_map
from listenbrainz_spark import config, hdfs_connection


RABBITMQ_HEARTBEAT_TIME = 2 * 60 * 60  # 2 hours -- a full dump import takes 40 minutes right now

logger = logging.getLogger(__name__)


class RequestConsumer:

    def __init__(self):
        self.redis_conn: Redis | None = None
        self.last_seen_id = None

    def get_result(self, request):
        try:
            query = request[b"query"].decode("utf-8")
            params = orjson.loads(request.get(b"params", "{}"))
        except Exception:
            logger.error('Bad query sent to spark request consumer: %s', json.dumps(request), exc_info=True)
            return None

        logger.info('Query: %s', query)
        logger.info('Params: %s', str(params))

        try:
            query_handler = listenbrainz_spark.query_map.get_query_handler(query)
        except KeyError:
            logger.error("Bad query sent to spark request consumer: %s", query, exc_info=True)
            return None
        except Exception as e:
            logger.error("Error while mapping query to function: %s", str(e), exc_info=True)
            return None

        try:
            # initialize connection to HDFS, the request consumer is a long running process
            # so we try to create a connection everytime before executing a query to avoid
            # affecting subsequent queries in case there's an intermittent connection issue
            hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
            return query_handler(**params)
        except TypeError as e:
            logger.error(
                "TypeError in the query handler for query '%s', maybe bad params. Error: %s", query, str(e), exc_info=True)
            return None
        except Exception as e:
            logger.error("Error in the query handler for query '%s': %s", query, str(e), exc_info=True)
            return None

    def push_to_result_queue(self, messages):
        logger.debug("Pushing result to RabbitMQ...")
        num_of_messages = 0
        avg_size_of_message = 0
        for message in messages:
            num_of_messages += 1
            body = orjson.dumps(message)
            avg_size_of_message += len(body)

            self.redis_conn.xadd(
                config.SPARK_RESULT_STREAM,
                {b"result": body},
                maxlen=config.SPARK_RESULT_STREAM_LEN,
                approximate=True
            )

        if num_of_messages:
            avg_size_of_message //= num_of_messages
            logger.info(f"Number of messages sent: {num_of_messages}")
            logger.info(f"Average size of message: {avg_size_of_message} bytes")
        else:
            logger.info("No messages calculated")

    def init_redis_connection(self):
        connection_name = "spark-request-consumer-" + socket.gethostname()
        self.redis_conn = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, client_name=connection_name)
        self.last_seen_id = self.redis_conn.get(config.SPARK_REQUEST_STREAM_LAST_SEEN) or b"0-0"

    def run(self):
        while True:
            streams = self.redis_conn.xread(
                {config.SPARK_REQUEST_STREAM: self.last_seen_id},
                count=1,
                block=5000
            )
            if not streams:
                continue

            logger.info('Received a request!')
            messages = streams[0][1]
            message_id, body = messages[0]

            messages = self.get_result(body)
            if messages:
                self.push_to_result_queue(messages)

            self.last_seen_id = message_id
            self.redis_conn.xtrim(config.SPARK_REQUEST_STREAM, minid=self.last_seen_id, approximate=False)
            self.redis_conn.set(config.SPARK_REQUEST_STREAM_LAST_SEEN, self.last_seen_id)
            logger.info('Request done!')

    def start(self, app_name):
        while True:
            try:
                logger.info('Request consumer started!')
                listenbrainz_spark.init_spark_session(app_name)
                self.init_redis_connection()
                self.run()
            except Exception as e:
                logger.critical("Error in spark-request-consumer: %s", str(e), exc_info=True)
                time.sleep(2)


def main(app_name):
    rc = RequestConsumer()
    rc.start(app_name)


if __name__ == '__main__':
    main('spark-writer')
