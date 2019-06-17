#!/usr/bin/env python3

import json
import sys
import os
import pika
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import ujson
import logging

from listenbrainz.listen import Listen
from time import time, sleep
from listenbrainz.listenstore import InfluxListenStore
from listenbrainz.listenstore import RedisListenStore
from listenbrainz.utils import escape, get_measurement_name, get_escaped_measurement_name, \
                               get_influx_query_timestamp, convert_to_unix_timestamp, \
                               convert_timestamp_to_influx_row_format
import listenbrainz.utils as utils

from listenbrainz.webserver import create_app
from flask import current_app
from requests.exceptions import ConnectionError
from redis import Redis
from collections import defaultdict

from listenbrainz.listen_writer import ListenWriter

class InfluxWriterSubscriber(ListenWriter):

    def __init__(self):
        super().__init__()

        self.ls = None
        self.influx = None
        self.incoming_ch = None
        self.unique_ch = None
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

        self._collect_and_log_stats(count, call_method=self.ls.update_listen_counts)

        return ret


    def insert_to_listenstore(self, data, retries=5):
        """
        Inserts a batch of listens to the ListenStore. If this fails, then breaks the data into
        two parts and recursively tries to insert them, until we find the culprit listen

        Args:
            data: the data to be inserted into the ListenStore
            retries: the number of retries to make before deciding that we've failed

        Returns: number of listens successfully sent
        """

        if not data:
            return 0

        failure_count = 0
        while True:
            try:
                self.ls.insert(data)
                return len(data)
            except (InfluxDBServerError, ValueError) as e:
                failure_count += 1
                if failure_count >= retries:
                    break
                sleep(self.ERROR_RETRY_DELAY)
            except InfluxDBClientError as e:
                current_app.logger.error("Cannot write data because of ClientError, data = %s" % str(data), exc_info=True)
                return 0
            except ConnectionError as e:
                current_app.logger.error("Cannot write data to listenstore: %s. Sleep." % str(e), exc_info=True)
                sleep(self.ERROR_RETRY_DELAY)

        # if we get here, we failed on trying to write the data
        if len(data) == 1:
            # try to send the bad listen one more time and if it doesn't work
            # log the error
            try:
                self.ls.insert(data)
                return 1
            except (InfluxDBServerError, InfluxDBClientError, ValueError, ConnectionError) as e:
                error_message = 'Unable to insert bad listen to listenstore: {error}, listen={json}'
                influx_dict = data[0].to_influx(get_measurement_name(data[0].user_name))
                current_app.logger.error(error_message.format(error=str(e), json=json.dumps(influx_dict, indent=3)), exc_info=True)
                return 0
        else:
            slice_index = len(data) // 2
            # send first half
            sent = self.insert_to_listenstore(data[:slice_index], retries)
            # send second half
            sent += self.insert_to_listenstore(data[slice_index:], retries)
            return sent


    def write(self, listen_dicts):
        submit = []
        unique = []
        duplicate_count = 0
        unique_count = 0

        # Partition the listens on the basis of user names
        # and then store the time range for each user
        users = {}
        for listen in listen_dicts:

            t = int(listen['listened_at'])
            user_name = listen['user_name']

            # if the timestamp is illegal, don't use it for ranges
            if t.bit_length() > 32:
                current_app.logger.error("timestamp %d is too large. listen: %s", t, json.dumps(listen, indent=3))
                continue

            if user_name not in users:
                users[user_name] = {
                    'min_time': t,
                    'max_time': t,
                    'listens': [listen],
                }
                continue

            if t > users[user_name]['max_time']:
                users[user_name]['max_time'] = t

            if t < users[user_name]['min_time']:
                users[user_name]['min_time'] = t

            users[user_name]['listens'].append(listen)

        # get listens in the time range for each user and
        # remove duplicates on the basis of timestamps
        for user_name in users:

            # get the range of time that we need to get from influx for
            # deduplication of listens
            min_time = users[user_name]['min_time']
            max_time = users[user_name]['max_time']

            query = """SELECT time, recording_msid
                         FROM %s
                        WHERE time >= %s
                          AND time <= %s
                    """ % (get_escaped_measurement_name(user_name), get_influx_query_timestamp(min_time), get_influx_query_timestamp(max_time))

            while True:
                try:
                    results = self.influx.query(query)
                    break
                except Exception as e:
                    current_app.logger.warn('Could not query influx, trying again: %s', str(e), exc_info=True)
                    sleep(3)

            # collect all the timestamps for this given time range.

            timestamps = defaultdict(list) # dict of list of listens indexed by timestamp
            for result in results.get_points(measurement=get_measurement_name(user_name)):
                timestamps[convert_to_unix_timestamp(result['time'])].append(result)

            for listen in users[user_name]['listens']:
                # Check if a listen with the same timestamp and recording msid is already present in
                # Influx DB and if it is, mark current listen as duplicate
                t = int(listen['listened_at'])
                recording_msid = listen['recording_msid']
                dup = False

                if t in timestamps:
                    for row in timestamps[t]:
                        if row['recording_msid'] == recording_msid:
                            duplicate_count += 1
                            dup = True
                            break
                    else:
                        # if there are listens with the same timestamp but different
                        # metadata, we add a tag specifically for making sure that
                        # influxdb doesn't drop one of the listens. This value
                        # is monotonically increasing and defaults to 0
                        listen['dedup_tag'] = len(timestamps[t])

                if not dup:
                    unique_count += 1
                    submit.append(Listen.from_json(listen))
                    unique.append(listen)
                    timestamps[t].append({
                        'time': convert_timestamp_to_influx_row_format(t),
                        'recording_msid': recording_msid
                    })

        t0 = time()
        submitted_count = self.insert_to_listenstore(submit)
        self.time += time() - t0

        current_app.logger.info("dups: %d, unique: %d, submitted: %d" % (duplicate_count, unique_count, submitted_count))
        if not unique_count:
            return True

        while True:
            try:
                self.unique_ch.basic_publish(
                    exchange=current_app.config['UNIQUE_EXCHANGE'],
                    routing_key='',
                    body=ujson.dumps(unique),
                    properties=pika.BasicProperties(delivery_mode = 2,),
                )
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()


        self.redis_listenstore.update_recent_listens(unique)

        return True


    def start(self):
        app = create_app()
        with app.app_context():
            current_app.logger.info("influx-writer init")
            self._verify_hosts_in_config()

            if "INFLUX_HOST" not in current_app.config:
                current_app.logger.critical("Influx service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
                sleep(self.ERROR_RETRY_DELAY)
                sys.exit(-1)

            while True:
                try:
                    self.ls = InfluxListenStore({
                        'REDIS_HOST': current_app.config['REDIS_HOST'],
                        'REDIS_PORT': current_app.config['REDIS_PORT'],
                        'REDIS_NAMESPACE': current_app.config['REDIS_NAMESPACE'],
                        'INFLUX_HOST': current_app.config['INFLUX_HOST'],
                        'INFLUX_PORT': current_app.config['INFLUX_PORT'],
                        'INFLUX_DB_NAME': current_app.config['INFLUX_DB_NAME'],
                    }, logger=current_app.logger)
                    self.influx = InfluxDBClient(
                        host=current_app.config['INFLUX_HOST'],
                        port=current_app.config['INFLUX_PORT'],
                        database=current_app.config['INFLUX_DB_NAME'],
                    )
                    break
                except Exception as err:
                    current_app.logger.error("Cannot connect to influx: %s. Retrying in 2 seconds and trying again." % str(err), exc_info=True)
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
                self.incoming_ch.queue_bind(exchange=current_app.config['INCOMING_EXCHANGE'], queue=current_app.config['INCOMING_QUEUE'])
                self.incoming_ch.basic_consume(
                    lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self),
                    queue=current_app.config['INCOMING_QUEUE'],
                )

                self.unique_ch = self.connection.channel()
                self.unique_ch.exchange_declare(exchange=current_app.config['UNIQUE_EXCHANGE'], exchange_type='fanout')

                current_app.logger.info("influx-writer started")
                try:
                    self.incoming_ch.start_consuming()
                except pika.exceptions.ConnectionClosed:
                    current_app.logger.warn("Connection to rabbitmq closed. Re-opening.", exc_info=True)
                    self.connection = None
                    continue

                self.connection.close()


if __name__ == "__main__":
    rc = InfluxWriterSubscriber()
    rc.start()
