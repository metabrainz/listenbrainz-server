#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from redis import Redis
from redis_pubsub import RedisPubSubSubscriber, NoSubscriberNameSetException, WriteFailException
from influxdb import InfluxDBClient, requests
import ujson
import logging
from listen import Listen
from time import time, sleep
import config

REPORT_FREQUENCY = 5000
SUBSCRIBER_NAME = "in"
KEYSPACE_NAME = "listen"

class InfluxWriterSubscriber(RedisPubSubSubscriber):
    def __init__(self, influx, redis):
        RedisPubSubSubscriber.__init__(self, redis, KEYSPACE_NAME)

        self.influx = influx
        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

    def write(self, listen_dicts):

        submit = []
        for listen in listen_dicts:
            meta = listen['track_metadata']
            data = {
                'measurement' : 'listen',
                'time' : int(listen['listened_at']) * 1000000000,
                'tags' : {
                    'user_name' : listen['user_name'],
                    'artist_msid' : meta['additional_info']['artist_msid'],
                    'album_msid' : meta['additional_info'].get('album_msid', ''),
                    'recording_msid' : listen['recording_msid'],
                },
                'fields' : {
                    'artist_name' : meta['additional_info'].get('artist_name', ''),
                    'artist_mbids' : ",".join(meta['additional_info'].get('artist_mbids', [])),
                    'album_name' : meta['additional_info'].get('release_name', ''),
                    'album_mbid' : meta['additional_info'].get('release_mbid', ''),
                    'track_name' : meta['track_name'],
                    'recording_mbid' : meta['additional_info'].get('recording_mbid', ''),
                    'tags' : ",".join(meta['additional_info'].get('tags', [])),
                }
            }
            submit.append(data)

        # TODO: Catch more exceptions?
        t0 = time()
        try:
            self.influx.write_points(submit)
        except requests.exceptions.ConnectionError as e:
            self.log.error("Cannot write data to influx: ", str(e))
            return False

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
                self.log.error("InfluxWriterSubscriber failed to write to Postgres.")
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
