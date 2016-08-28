#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from redis import Redis
from redis_keys import REDIS_LISTEN_JSON, REDIS_LISTEN_JSON_REFCOUNT, REDIS_LISTEN_CONSUMER_IDS, \
    REDIS_LISTEN_CONSUMERS, REDIS_LISTEN_CONSUMER_IDS_PENDING
import config
from influxdb import InfluxDBClient

import ujson
import json # TODO: used for debugging. remove before submitting PR
import logging
import calendar
from listen import Listen
from time import time, sleep

BATCH_SIZE = 1000
REPORT_FREQUENCY = 5000
BATCH_TIMEOUT = 5      # in seconds. Don't let a listen get older than this before writing
REQUEST_TIMEOUT = 1    # in seconds. Wait this long to get a listen from redis

CONSUMER_NAME = "in"

# Things left to do
#   Redis persistence
#   Use the two lists model in order to not lose any items in case of restart
#   Avoid duplication in BigQuery

class InfluxDBWriter(object):
    def __init__(self):
        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

    def _register_self(self, r):
        consumers = r.smembers(REDIS_LISTEN_CONSUMERS)
        if not CONSUMER_NAME in consumers:
            r.sadd(REDIS_LISTEN_CONSUMERS, CONSUMER_NAME)

    def start(self, redis_host):

        self.log.debug("InfluxDBWriter started")

        r = Redis(redis_host)
        self._register_self(r)

        # If we have listens on the pending list, lets move them back to the submission list
        ids = r.lrange(REDIS_LISTEN_CONSUMER_IDS_PENDING + CONSUMER_NAME, 0, -1)
        if ids:
            r.lpush(REDIS_LISTEN_CONSUMER_IDS + CONSUMER_NAME, *ids)
            r.ltrim(REDIS_LISTEN_CONSUMER_IDS_PENDING + CONSUMER_NAME, 1, 0)

        # 0 indicates that we've received no listens yet
        batch_start_time = 0 
        while True:
            listens = []
            listen_ids = []

            while True:
                id = r.brpoplpush(REDIS_LISTEN_CONSUMER_IDS + CONSUMER_NAME, 
                    REDIS_LISTEN_CONSUMER_IDS_PENDING + CONSUMER_NAME, REQUEST_TIMEOUT)
                # If we got an id, fetch the listen and add to our list 
                if id:
                    listen = r.get(REDIS_LISTEN_JSON + id)
                    if listen:
                        listen_ids.append(id)
                        data = ujson.loads(listen)
                        l = Listen().from_json(data)
                        if l.validate():
                            # record the time when we get a first listen in this batch
                            if not batch_start_time:
                                batch_start_time = time()
                            listens.append(l)
                        else:
                            self.log.error("invalid listen: " + str(l))

                    else:
                        # TODO: What happens if we don't get a listen?
                        pass

                if time() - batch_start_time >= BATCH_TIMEOUT:
                    break

                if len(listens) >= BATCH_SIZE:
                    break

            if not listens:
                batch_start_time = 0
                continue

            self.log.error("got %d listens" % len(listens))
            # We've collected listens to write, now write them

            # Clear the start time, since we've cleaned out the batch
            batch_start_time = 0

            # clear the listens-pending list
            r.ltrim(REDIS_LISTEN_CONSUMER_IDS_PENDING + CONSUMER_NAME, 1, 0)

            # now clean up the listens from redis
            for id in listen_ids:
                # Get the refcount for this listen. If 0, delete it and the refcount
                refcount = r.decr(REDIS_LISTEN_JSON_REFCOUNT + id)
                if refcount == 0:
                    r.delete(REDIS_LISTEN_JSON + id)
                    r.delete(REDIS_LISTEN_JSON_REFCOUNT + id)

            # collect and occasionally print some stats
            self.inserts += len(listens)
            if self.inserts >= REPORT_FREQUENCY:
                self.total_inserts += self.inserts
                self.log.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                    (self.inserts, self.time, self.inserts / self.time, self.total_inserts))
                self.inserts = 0
                self.time = 0

if __name__ == "__main__":
    rc = InfluxDBWriter()
    rc.start(config.REDIS_HOST)
