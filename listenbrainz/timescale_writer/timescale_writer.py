#!/usr/bin/env python3

import json
import sys
import os
import pika
import ujson
import logging
from time import time, sleep
from listenbrainz.webserver import create_app
from flask import current_app

from listenbrainz.listen import Listen
from listenbrainz.listen_writer import ListenWriter
import psycopg2
from psycopg2.errors import OperationalError, DuplicateTable, UntranslatableCharacter
from psycopg2.extras import execute_values

import sys, traceback

TIMESCALE_QUEUE = "ts_incoming"

class TimescaleWriterSubscriber(ListenWriter):

    def __init__(self):
        super().__init__()

        self.timescale = None
        self.incoming_ch = None
        self.redis_listenstore = None


    def callback(self, ch, method, properties, body):
        listens = ujson.loads(body)
        ret = self.write(listens)
        if not ret:
            return ret

        while True:
            try:
                self.incoming_ch.basic_ack(delivery_tag = method.delivery_tag)
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()

        count = len(listens)

#        self._collect_and_log_stats(count, call_method=self.ls.update_listen_counts)

        return ret


    def write(self, listens):
        '''
            This is quick and dirty for a proof of concept. Errors are logged, but data ruthlessly discarded.
        '''

        if not listens:
            return 0

        to_insert = []
        for listen in listens:
            tm = listen['track_metadata']
            # Clean up null characters in the data
            if 'artist_name' in tm and tm['artist_name']:
                tm['artist_name'] = tm['artist_name'].replace("\u0000", "")
            if 'track_name' in tm and tm['track_name']:
                 tm['track_name'] = tm['track_name'].replace("\u0000", "")
            if 'release_name' in tm and tm['release_name']:
                tm['release_name'] = tm['release_name'].replace("\u0000", "")

            to_insert.append([
                    listen['listened_at'],
                    listen['recording_msid'],
                    listen['user_name'],
                    ujson.dumps(tm)])

        with self.conn.cursor() as curs:
            # TODO: Later add this line to the query and pass the results down to the unique rmq
            query = """INSERT INTO listen 
                            VALUES %s
                       ON CONFLICT (listened_at, recording_msid, user_name)
                        DO NOTHING
                         RETURNING listened_at, recording_msid, user_name, data
                    """
            try:
                execute_values(curs, query, to_insert, template=None)
                result = curs.fetchone()
                self.conn.commit()
            except psycopg2.OperationalError as err:
                print("Cannot write data to timescale: %s." % str(err))
                return 0
            except Exception as err:
                print("Cannot write data to timescale: %s. Sleep." % str(err))
                traceback.print_exc()
                return 0

        return len(to_insert)


    def start(self):
        app = create_app()
        with app.app_context():
            print("timescale-writer init")
            self._verify_hosts_in_config()

            try:
                with psycopg2.connect(current_app.config['SQLALCHEMY_TIMESCALE_URI']) as conn:
                    print("connected to timescale")
                    self.conn = conn
                    while True:
                        self.connect_to_rabbitmq()
                        self.incoming_ch = self.connection.channel()
                        self.incoming_ch.exchange_declare(exchange=current_app.config['INCOMING_EXCHANGE'], exchange_type='fanout')
                        self.incoming_ch.queue_declare(current_app.config['INCOMING_QUEUE'], durable=True)
                        self.incoming_ch.queue_bind(exchange=current_app.config['INCOMING_EXCHANGE'], queue=TIMESCALE_QUEUE)
                        self.incoming_ch.basic_consume(
                            lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self),
                            queue=TIMESCALE_QUEUE,
                        )

                        print("timescale-writer started")
                        try:
                            self.incoming_ch.start_consuming()
                        except pika.exceptions.ConnectionClosed:
                            current_app.logger.warn("Connection to rabbitmq closed. Re-opening.", exc_info=True)
                            self.connection = None
                            continue

                        self.connection.close()
            except Exception as err:
                traceback.print_exc()
                print("failed to start timescale loop ", str(err))

            self.conn = None


if __name__ == "__main__":
    rc = TimescaleWriterSubscriber()
    rc.start()
