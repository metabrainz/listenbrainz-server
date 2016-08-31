#!/usr/bin/env python

import sys
import os
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from redis import Redis
from redis_pubsub import RedisPubSubSubscriber, RedisPubSubPublisher, NoSubscriberNameSetException, WriteFailException, NoSubscribersException
from influxdb import InfluxDBClient
import ujson
import logging
from listen import Listen
from time import time, sleep
import config

REPORT_FREQUENCY = 5000
SUBSCRIBER_NAME = "in"
KEYSPACE_NAME_INCOMING = "ilisten"
KEYSPACE_NAME_UNIQUE = "ulisten"

class InfluxWriterSubscriber(RedisPubSubSubscriber):
    def __init__(self, influx, redis):
        RedisPubSubSubscriber.__init__(self, redis, KEYSPACE_NAME_INCOMING)

        self.publisher = RedisPubSubPublisher(redis, KEYSPACE_NAME_UNIQUE)

        self.influx = influx
        self.log = logging.getLogger(__name__)
        logging.basicConfig()
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
        results = i.query(query)

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

            meta = listen['track_metadata']
            data = {
                'measurement' : 'listen',
                'time' : t,
                'tags' : {
                    'user_name' : listen['user_name'],
                    'artist_msid' : meta['additional_info']['artist_msid'],
                    'album_msid' : meta['additional_info'].get('album_msid', ''),
                    'recording_msid' : listen['recording_msid'],
                },
                'fields' : {
                    'artist_name' : meta['artist_name'],
                    'artist_mbids' : ",".join(meta['additional_info'].get('artist_mbids', [])),
                    'album_name' : meta['additional_info'].get('release_name', ''),
                    'album_mbid' : meta['additional_info'].get('release_mbid', ''),
                    'track_name' : meta['track_name'],
                    'recording_mbid' : meta['additional_info'].get('recording_mbid', ''),
                    'tags' : ",".join(meta['additional_info'].get('tags', [])),
                }
            }
            submit.append(data)
            unique.append(listen)

        self.log.error("dups: %d, unique %d" % (duplicate_count, unique_count))
        if not unique_count:
            return True

        t0 = time()
        try:
            if not self.influx.write_points(submit, time_precision='s'):
                self.log.error("Cannot write data to influx. (write_points returned False)")
                return False
        except ValueError as e:
            self.log.error("Cannot write data to influx: %s" % str(e))
            return False

        try:
            self.publisher.publish(unique)
        except NoSubscribersException:
            self.log.error("No subscribers, cannot publish unique listens.")

        self.time += time() - t0

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
                self.log.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                    (count, self.time, count / self.time, self.total_inserts))
                self.inserts = 0
                self.time = 0

if __name__ == "__main__":
    r = Redis(config.REDIS_HOST)
    i = InfluxDBClient(host=config.INFLUX_HOST, port=config.INFLUX_PORT, database=config.INFLUX_DB)
    rc = InfluxWriterSubscriber(i, r)
    rc.start()
