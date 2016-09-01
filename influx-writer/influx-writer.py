#!/usr/bin/env python

import sys
import os
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "listenstore"))
from redis import Redis
from redis_pubsub import RedisPubSubSubscriber, RedisPubSubPublisher, NoSubscriberNameSetException, WriteFailException, NoSubscribersException
from influxdb import InfluxDBClient
import ujson
import logging
from listen import Listen
from time import time, sleep
import config
from listenstore.listenstore import InfluxListenStore

REPORT_FREQUENCY = 5000
SUBSCRIBER_NAME = "in"
KEYSPACE_NAME_INCOMING = "ilisten"
KEYSPACE_NAME_UNIQUE = "ulisten"

class InfluxWriterSubscriber(RedisPubSubSubscriber):
    def __init__(self, ls, influx, redis):
        RedisPubSubSubscriber.__init__(self, redis, KEYSPACE_NAME_INCOMING)

        self.publisher = RedisPubSubPublisher(redis, KEYSPACE_NAME_UNIQUE)

        self.influx = influx
        self.ls = ls
        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.log.setLevel(logging.INFO)
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

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

        try:
            t0 = time()
            self.ls.insert(submit)
            self.time += time() - t0
        except ValueError as e:
            self.log.error("Cannot write data to listenstore: %s" % str(e))
            return False

        try:
            self.publisher.publish(unique)
        except NoSubscribersException:
            self.log.error("No subscribers, cannot publish unique listens.")

        return True

    def start(self):
        self.log.info("InfluxWriterSubscriber started")

        self.register(SUBSCRIBER_NAME)
        while True:
            try:
                count = self.subscriber()            
            except NoSubscriberNameSetException as e:
                self.log.error("InfluxWriterSubscriber has no subscriber name set.")
                return
            except WriteFailException as e:
                self.log.error("InfluxWriterSubscriber failed to write: %s" % str(e))
                return

            if not count:
                continue

            # collect and occasionally print some stats
            self.inserts += count
            if self.inserts >= REPORT_FREQUENCY:
                self.total_inserts += self.inserts
                if self.time > 0:
                    self.log.error("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                        (count, self.time, count / self.time, self.total_inserts))
                self.inserts = 0
                self.time = 0

if __name__ == "__main__":
    ls = InfluxListenStore({ 'REDIS_HOST' : config.REDIS_HOST, 
                             'INFLUX_HOST': config.INFLUX_HOST,
                             'INFLUX_PORT': config.INFLUX_PORT,
                             'INFLUX_DB': config.INFLUX_DB})
    i = InfluxDBClient(host=config.INFLUX_HOST, port=config.INFLUX_PORT, database=config.INFLUX_DB)
    r = Redis(config.REDIS_HOST)
    rc = InfluxWriterSubscriber(ls, i, r)
    rc.start()
