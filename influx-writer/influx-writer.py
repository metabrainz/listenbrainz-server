#!/usr/bin/env python
from __future__ import print_function

import sys
import os
import pika
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import ujson
import logging
from listen import Listen
from time import time, sleep
import config
from listenstore import InfluxListenStore
from requests.exceptions import ConnectionError

REPORT_FREQUENCY = 5000
KEYSPACE_NAME_UNIQUE = "ulisten"
DUMP_JSON_WITH_ERRORS = False
ERROR_RETRY_DELAY = 3 # number of seconds to wait until retrying an operation


# TODO: Consider persistence and acknowledgements
class InfluxWriterSubscriber(object):
    def __init__(self, ls, influx):
        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.log.setLevel(logging.INFO)
        while True:
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=config.RABBITMQ_HOST, port=config.RABBITMQ_PORT))
                break
            except pika.exceptions.ConnectionClosed:
                print("Cannot connect to rabbitmq, sleeping 2 seconds")
                sleep(2)

        self.incoming_ch = self.connection.channel()
        self.incoming_ch.exchange_declare(exchange='incoming', type='fanout')
        self.incoming_ch.queue_declare('incoming', durable=True)
        self.incoming_ch.queue_bind(exchange='incoming', queue='incoming')
        self.incoming_ch.basic_consume(lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self), queue='incoming')

        self.unique_ch = self.connection.channel()
        self.unique_ch.exchange_declare(exchange='unique', type='fanout')
        self.unique_ch.queue_declare('unique', durable=True)

        self.influx = influx
        self.ls = ls
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0


    @staticmethod
    def static_callback(ch, method, properties, body, obj):
        return obj.callback(ch, method, properties, body)


    def callback(self, ch, method, properties, body):
        listens = ujson.loads(body)
        ret = self.write(listens)
        if not ret:
            return ret

        self.incoming_ch.basic_ack(delivery_tag = method.delivery_tag)

        # collect and occasionally print some stats
        self.inserts += len(listens)
        if self.inserts >= REPORT_FREQUENCY:
            self.total_inserts += self.inserts
            if self.time > 0:
                self.print_and_log_error("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                    (self.inserts, self.time, self.inserts / self.time, self.total_inserts))
            self.inserts = 0
            self.time = 0

        return ret


    def write(self, listen_dicts):
        submit = []
        unique = []

        # Calculate the time range that this set of listens coveres
        min_time = 0
        max_time = 0
        user_name = ""
        for listen in listen_dicts:
            t = int(listen['listened_at'])
            if not max_time:
                min_time = max_time = t
                user_name = listen['user_name']
                continue

            if t > max_time:
                max_time = t

            if t < min_time:
                min_time = t

        # Quote single quote characters which could be used to mount an injection attack.
        # Sadly, influxdb does not provide a means to do this in the client library
        user_name = user_name.replace("'", "\'")

        # quering for artist name here, since a field must be included in the query.
        query = """SELECT time, artist_name
                     FROM listen
                    WHERE user_name = '%s'
                      AND time >= %d000000000
                      AND time <= %d000000000
                """ % (user_name, min_time, max_time)
        while True:
            try:
                results = i.query(query)
                break
            except Exception as e:
                self.log.error("Cannot query influx: %s" % str(e))
                sleep(3)

        # collect all the timestamps for this given time range.
        timestamps = {}
        for result in results.get_points(measurement='listen'):
            dt = datetime.strptime(result['time'] , "%Y-%m-%dT%H:%M:%SZ")
            timestamps[int(dt.strftime('%s'))] = 1

        duplicate_count = 0
        unique_count = 0
        for listen in listen_dicts:
            # Check to see if the timestamp is already in the DB
            t = int(listen['listened_at'])
            if t in timestamps:
                duplicate_count += 1
                continue

            unique_count += 1
            submit.append(Listen().from_json(listen))
            unique.append(listen)

        self.log.error("dups: %d, unique %d" % (duplicate_count, unique_count))
        if not unique_count:
            return True

        # TODO: handle this: ERROR Cannot write data to listenstore: {"error":"timeout"}
        while True:
            try:
                t0 = time()
                self.ls.insert(submit)
                self.time += time() - t0
                break

            except ConnectionError as e:
                self.log.error("Cannot write data to listenstore: %s. Sleep." % str(e))
                sleep(ERROR_RETRY_DELAY)
                continue

            except (InfluxDBClientError, InfluxDBServerError, ValueError) as e:
                self.log.error("Cannot write data to listenstore: %s" % str(e))
                if DUMP_JSON_WITH_ERRORS:
                    self.log.error("Was writing the following data: ")
                    self.log.error(json.dumps(submit, indent=4))
                return False

        # TODO: Add error handling here
        self.unique_ch.basic_publish(exchange='unique', routing_key='', body=ujson.dumps(unique), 
            properties=pika.BasicProperties(delivery_mode = 2,))

        return True

    def start(self):
        self.log.info("InfluxWriterSubscriber started")
        self.incoming_ch.start_consuming()
        self.connection.close()

    def print_and_log_error(self, msg):
        self.log.error(msg)
        print(msg, file = sys.stderr)

if __name__ == "__main__":
    ls = InfluxListenStore({ 'REDIS_HOST' : config.REDIS_HOST,
                             'REDIS_PORT' : config.REDIS_PORT,
                             'INFLUX_HOST': config.INFLUX_HOST,
                             'INFLUX_PORT': config.INFLUX_PORT,
                             'INFLUX_DB_NAME': config.INFLUX_DB_NAME})
    i = InfluxDBClient(host=config.INFLUX_HOST, port=config.INFLUX_PORT, database=config.INFLUX_DB_NAME)
    rc = InfluxWriterSubscriber(ls, i)
    rc.start()
