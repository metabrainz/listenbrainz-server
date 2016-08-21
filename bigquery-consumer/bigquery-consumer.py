#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../listenstore"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from redis import Redis
from redis_keys import REDIS_LISTEN_JSON, REDIS_LISTEN_JSON_REFCOUNT, REDIS_LISTEN_CONSUMER_IDS, \
    REDIS_LISTEN_CONSUMERS
import config

import ujson
import logging
from listenstore.listenstore import Listen
from time import time, sleep

BATCH_SIZE = 1000
REPORT_FREQUENCY = 5000
BATCH_TIMEOUT = 3      # in seconds. Don't let a listen get older than this before writing
REQUEST_TIMEOUT = 1    # in seconds. Wait this long to get a listen from redis

CONSUMER_NAME = "bq"

class BigQueryConsumer(object):
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

    def _register_self(self, r):
        consumers = r.smembers(REDIS_LISTEN_CONSUMERS)
        if not CONSUMER_NAME in consumers:
            r.sadd(REDIS_LISTEN_CONSUMERS, CONSUMER_NAME)

    def start(self, database_uri, redis_host):
        self.log.info("BiqQueryListenConsumer started")

        r = Redis(redis_host)
        self._register_self(r)

        # 0 indicates that we've received no listens yet
        batch_start_time = 0 
        while True:
            listens = []
            listen_ids = []

            while True:
                id = r.blpop(REDIS_LISTEN_CONSUMER_IDS + CONSUMER_NAME, REQUEST_TIMEOUT)
                # If we got an id, fetch the listen and add to our list 
                if id:
                    id = id[1]
                    # record the time when we get a first listen in this batch
                    if not batch_start_time:
                        batch_start_time = time()

                    listen = r.get(REDIS_LISTEN_JSON + id)
                    if listen:
                        listen_ids.append(id)
                        data = ujson.loads(listen)
                        l = Listen().from_json(data)
                        if l.validate():
                            listens.append(l)
                        else:
                            self.log.error("invalid listen: " + str(l))

                    else:
                        # TODO: What happens if we don't get a listen?
                        pass

                if time() - batch_start_time >= BATCH_TIMEOUT:
                    break

            # We've collected listens to write, now write them
            # TODO

            # Clear the start time, since we've cleaned out the batch
            batch_start_time = 0

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
    rc = BigQueryConsumer()
    rc.start(config.SQLALCHEMY_DATABASE_URI, config.REDIS_HOST)
