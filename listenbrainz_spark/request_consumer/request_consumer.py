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

import os
import pika
import uuid
import json
import sys
import time

import listenbrainz_spark
import listenbrainz_spark.query_map
from datetime import datetime
from listenbrainz_spark.utils import init_rabbitmq
from flask import current_app

from py4j.protocol import Py4JJavaError

class RequestConsumer:

    def get_result(self, request):
        try:
            query = request['query']
            params = request.get('params', {})
        except Exception:
            current_app.logger.error('Bad query sent to spark request consumer: %s', json.dumps(request), exc_info=True)
            return None

        try:
            query_handler = listenbrainz_spark.query_map.get_query_handler(query)
        except KeyError:
            current_app.logger.error("Bad query sent to spark request consumer: %s", query, exc_info=True)
            return None
        except Exception as e:
            current_app.logger.error("Error while mapping query to function: %s", str(e), exc_info=True)
            return None

        try:
            return query_handler(**params)
        except TypeError as e:
            current_app.logger.error("TypeError in the query handler for query '%s', maybe bad params. Error: %s", query, str(e), exc_info=True)
            return None
        except Exception as e:
            current_app.logger.error("Error in the query handler for query '%s': %s", query, str(e), exc_info=True)
            return None


    def push_to_result_queue(self, messages):
        for message in messages:
            while True:
                try:
                    self.result_channel.basic_publish(
                        exchange=current_app.config['SPARK_RESULT_EXCHANGE'],
                        routing_key='',
                        body=json.dumps(message),
                        properties=pika.BasicProperties(delivery_mode = 2,),
                    )
                    break
                except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed) as e:
                    current_app.logger.error('RabbitMQ Connection error while publishing results: %s', str(e), exc_info=True)
                    time.sleep(1)
                    self.rabbitmq.close()
                    self.connect_to_rabbitmq()
                    self.init_rabbitmq_channels()


    def callback(self, channel, method, properties, body):
        request = json.loads(body.decode('utf-8'))
        messages = self.get_result(request)
        if messages:
            self.push_to_result_queue(messages)
        while True:
            try:
                self.request_channel.basic_ack(delivery_tag=method.delivery_tag)
                break
            except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed) as e:
                current_app.logger.error('RabbitMQ Connection error when acknowledging request: %s', str(e), exc_info=True)
                time.sleep(1)
                self.rabbitmq.close()
                self.connect_to_rabbitmq()
                self.init_rabbitmq_channels()


    def connect_to_rabbitmq(self):
        self.rabbitmq = init_rabbitmq(
            username=current_app.config['RABBITMQ_USERNAME'],
            password=current_app.config['RABBITMQ_PASSWORD'],
            host=current_app.config['RABBITMQ_HOST'],
            port=current_app.config['RABBITMQ_PORT'],
            vhost=current_app.config['RABBITMQ_VHOST'],
            log=current_app.logger.critical,
        )

    def init_rabbitmq_channels(self):
        self.request_channel = self.rabbitmq.channel()
        self.request_channel.exchange_declare(exchange=current_app.config['SPARK_REQUEST_EXCHANGE'], exchange_type='fanout')
        self.request_channel.queue_declare(current_app.config['SPARK_REQUEST_QUEUE'], durable=True)
        self.request_channel.queue_bind(exchange=current_app.config['SPARK_REQUEST_EXCHANGE'], queue=current_app.config['SPARK_REQUEST_QUEUE'])
        self.request_channel.basic_consume(self.callback, queue=current_app.config['SPARK_REQUEST_QUEUE'])

        self.result_channel = self.rabbitmq.channel()
        self.result_channel.exchange_declare(exchange=current_app.config['SPARK_RESULT_EXCHANGE'], exchange_type='fanout')

    def run(self):
        while True:
            try:
                self.connect_to_rabbitmq()
                self.init_rabbitmq_channels()
                current_app.logger.info('Request consumer started!')

                try:
                    self.request_channel.start_consuming()
                except pika.exceptions.ConnectionClosed as e:
                    current_app.logger.error('connection to rabbitmq closed: %s', str(e), exc_info=True)
                    self.rabbitmq.close()
                    continue
                self.rabbitmq.close()
            except Py4JJavaError as e:
                current_app.logger.critical("Critical: JAVA error in spark-request consumer: %s, message: %s", str(e), str(e.java_exception), exc_info=True)
                time.sleep(2)
            except Exception as e:
                current_app.logger.critical("Error in spark-request-consumer: %s", str(e), exc_info=True)
                time.sleep(2)


def main(app_name):
    listenbrainz_spark.init_spark_session(app_name)
    RequestConsumer().run()


if __name__ == '__main__':
    main('spark-writer')
