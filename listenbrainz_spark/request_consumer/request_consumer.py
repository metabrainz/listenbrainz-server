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


    def push_to_result_queue(self, result):
        while True:
            try:
                self.result_channel.basic_publish(
                    exchange=current_app.config['SPARK_RESULT_EXCHANGE'],
                    routing_key='',
                    body=json.dumps(result),
                    properties=pika.BasicProperties(delivery_mode = 2,),
                )
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()
                time.sleep(1)
            except pika.exceptions.ChannelClosed:
                self.result_channel = self.rabbitmq.channel()
                self.result_channel.exchange_declare(exchange=current_app.config['SPARK_RESULT_EXCHANGE'], exchange_type='fanout')



    def callback(self, channel, method, properties, body):
        current_app.logger.info("Processing new request...")
        request = json.loads(body.decode('utf-8'))
        current_app.logger.info("Calculating result...")
        result = self.get_result(request)
        current_app.logger.info("Done!")
        if result:
            current_app.logger.info("Pushing to result queue...")
            self.push_to_result_queue(result)
            current_app.logger.info("Done!")
        while True:
            try:
                self.request_channel.basic_ack(delivery_tag=method.delivery_tag)
                break
            except pika.exceptions.ChannelClosed:
                self.request_channel = self.rabbitmq.channel()
                self.request_channel.exchange_declare(exchange=current_app.config['SPARK_REQUEST_EXCHANGE'], exchange_type='fanout')
                self.request_channel.queue_declare(current_app.config['SPARK_REQUEST_QUEUE'], durable=True)
                self.request_channel.queue_bind(exchange=current_app.config['SPARK_REQUEST_EXCHANGE'], queue=current_app.config['SPARK_REQUEST_QUEUE'])
                self.request_channel.basic_consume(self.callback, queue=current_app.config['SPARK_REQUEST_QUEUE'])


        current_app.logger.info("Request processed!")


    def connect_to_rabbitmq(self):
        self.rabbitmq = init_rabbitmq(
            username=current_app.config['RABBITMQ_USERNAME'],
            password=current_app.config['RABBITMQ_PASSWORD'],
            host=current_app.config['RABBITMQ_HOST'],
            port=current_app.config['RABBITMQ_PORT'],
            vhost=current_app.config['RABBITMQ_VHOST'],
            log=current_app.logger.critical,
        )


    def run(self):
        while True:
            current_app.logger.info("Connecting to RabbitMQ...")
            self.connect_to_rabbitmq()
            current_app.logger.info("Connected!")
            self.request_channel = self.rabbitmq.channel()
            self.request_channel.exchange_declare(exchange=current_app.config['SPARK_REQUEST_EXCHANGE'], exchange_type='fanout')
            self.request_channel.queue_declare(current_app.config['SPARK_REQUEST_QUEUE'], durable=True)
            self.request_channel.queue_bind(exchange=current_app.config['SPARK_REQUEST_EXCHANGE'], queue=current_app.config['SPARK_REQUEST_QUEUE'])
            self.request_channel.basic_consume(self.callback, queue=current_app.config['SPARK_REQUEST_QUEUE'])

            self.result_channel = self.rabbitmq.channel()
            self.result_channel.exchange_declare(exchange=current_app.config['SPARK_RESULT_EXCHANGE'], exchange_type='fanout')

            current_app.logger.info('Started request consumer...')
            try:
                self.request_channel.start_consuming()
            except pika.exceptions.ConnectionClosed:
                current_app.logger.error('connection to rabbitmq closed.', exc_info=True)
                continue
            self.rabbitmq.close()


def main(app_name):
    listenbrainz_spark.init_spark_session(app_name)
    RequestConsumer().run()


if __name__ == '__main__':
    main('spark-writer')
