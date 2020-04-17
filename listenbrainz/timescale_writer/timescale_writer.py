#!/usr/bin/env python3

import json
import sys
import os
import pika
import ujson
import logging
import traceback
import calendar

from flask import current_app
from requests.exceptions import ConnectionError
from redis import Redis
from collections import defaultdict
from operator import itemgetter
import psycopg2
from psycopg2.errors import OperationalError, DuplicateTable, UntranslatableCharacter

from listenbrainz.listen import Listen
from time import time, sleep
from listenbrainz.listenstore import RedisListenStore
import listenbrainz.utils as utils
from listenbrainz.listen_writer import ListenWriter
from listenbrainz.listenstore import TimescaleListenStore
from listenbrainz.webserver import create_app

# We need to use different incoming queues and unique exchanges in order to co-exist with the unflux setup
# for testing. We will need to undo these before releasing:
TIMESCALE_INCOMING_QUEUE = "incoming"
TIMESCALE_UNIQUE_EXCHANGE = "unique"

class TimescaleWriterSubscriber(ListenWriter):

    def __init__(self):
        super().__init__()

        self.ls = None
        self.incoming_ch = None
        self.unique_ch = None
        self.redis_listenstore = None


    def callback(self, ch, method, properties, body):

        listens = ujson.loads(body)

        submit = []
        for listen in listens:
            submit.append(Listen.from_json(listen))
        ret = self.insert_to_listenstore(submit)

        if not ret:
            return ret

        while True:
            try:
                self.incoming_ch.basic_ack(delivery_tag = method.delivery_tag)
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()

        return ret


    def insert_to_listenstore(self, data):
        """
        Inserts a batch of listens to the ListenStore. Timescale will report back as 
        to which rows were actually inserted into the DB, allowing us to send those
        down the unique queue.

        Args:
            data: the data to be inserted into the ListenStore
            retries: the number of retries to make before deciding that we've failed

        Returns: number of listens successfully sent
        """


        if not data:
            return 0

        try:
            rows_inserted = self.ls.insert(data)
        except psycopg2.OperationalError as err:
            current_app.logger.error("Cannot write data to listenstore: %s. Sleep." % str(e), exc_info=True)
            sleep(self.ERROR_RETRY_DELAY)
            return 0

        if not rows_inserted:
            return 0

        unique = []
        inserted_index = {}
        for inserted in rows_inserted:
            inserted_index['%d-%s-%s' % (inserted[0], inserted[1], inserted[2])] = 1

        for listen in data:
            k = '%d-%s-%s' % (listen.ts_since_epoch, listen.recording_msid, listen.user_name)
            if k in inserted_index:
                unique.append(listen)

        if not unique:
            return len(rows_inserted)

        while True:
            try:
                self.unique_ch.basic_publish(
                    exchange=TIMESCALE_UNIQUE_EXCHANGE,
                    routing_key='',
                    body=ujson.dumps(unique),
                    properties=pika.BasicProperties(delivery_mode = 2,),
                )
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()


        self.redis_listenstore.update_recent_listens(unique)

        return len(rows_inserted)


    def start(self):
        app = create_app()
        with app.app_context():
            current_app.logger.info("timescale-writer init")
            self._verify_hosts_in_config()

            if "SQLALCHEMY_TIMESCALE_URI" not in current_app.config:
                current_app.logger.critical("Timescale service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
                sleep(self.ERROR_RETRY_DELAY)
                sys.exit(-1)

            try:
                while True:
                    try:
                        self.ls = TimescaleListenStore({
                            'REDIS_HOST': current_app.config['REDIS_HOST'],
                            'REDIS_PORT': current_app.config['REDIS_PORT'],
                            'REDIS_NAMESPACE': current_app.config['REDIS_NAMESPACE'],
                            'SQLALCHEMY_TIMESCALE_URI': current_app.config['SQLALCHEMY_TIMESCALE_URI']
                        }, logger=current_app.logger)
                        break
                    except Exception as err:
                        current_app.logger.error("Cannot connect to timescale: %s. Retrying in 2 seconds and trying again." % str(err), exc_info=True)
                        sleep(self.ERROR_RETRY_DELAY)

                while True:
                    try:
                        self.redis = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'], decode_responses=True)
                        self.redis.ping()
                        self.redis_listenstore = RedisListenStore(current_app.logger, current_app.config)
                        break
                    except Exception as err:
                        current_app.logger.error("Cannot connect to redis: %s. Retrying in 2 seconds and trying again." % str(err), exc_info=True)
                        sleep(self.ERROR_RETRY_DELAY)

                while True:
                    self.connect_to_rabbitmq()
                    self.incoming_ch = self.connection.channel()
                    self.incoming_ch.exchange_declare(exchange=current_app.config['INCOMING_EXCHANGE'], exchange_type='fanout')
                    self.incoming_ch.queue_declare(current_app.config['INCOMING_QUEUE'], durable=True)
                    self.incoming_ch.queue_bind(exchange=current_app.config['INCOMING_EXCHANGE'], queue=TIMESCALE_INCOMING_QUEUE)
                    self.incoming_ch.basic_consume(
                        lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self),
                        queue=TIMESCALE_INCOMING_QUEUE,
                    )

                    self.unique_ch = self.connection.channel()
                    self.unique_ch.exchange_declare(exchange=TIMESCALE_UNIQUE_EXCHANGE, exchange_type='fanout')

                    try:
                        self.incoming_ch.start_consuming()
                    except pika.exceptions.ConnectionClosed:
                        current_app.logger.warn("Connection to rabbitmq closed. Re-opening.", exc_info=True)
                        self.connection = None
                        continue

                    self.connection.close()


            except Exception as err:
                traceback.print_exc()
                current_app.logger.error("failed to start timescale loop ", str(err))


if __name__ == "__main__":
    rc = TimescaleWriterSubscriber()
    rc.start()
