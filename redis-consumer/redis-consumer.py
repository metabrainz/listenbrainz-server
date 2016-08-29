#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../listenstore"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from redis import Redis
from redis_pubsub import RedisPubSubSubscriber, NoSubscriberNameSetException, WriteFailException
import config

import ujson
import logging
from listen import Listen
from listenstore.listenstore import PostgresListenStore
from time import time, sleep

REPORT_FREQUENCY = 5000
SUBSCRIBER_NAME = "pg"
KEYSPACE_NAME = "listen"

class RedisConsumer(RedisPubSubSubscriber):
    def __init__(self, redis, database_uri):
        RedisPubSubSubscriber.__init__(self, redis, KEYSPACE_NAME)

        self.log = logging.getLogger(__name__)
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0
        self.ls = PostgresListenStore({
          'SQLALCHEMY_DATABASE_URI': database_uri,
        })

    def write(self, listen_dicts):
        t0 = time()
        listens = []
        for listen in listen_dicts:
            listens.append(Listen().from_json(listen))
        self.ls.insert(listens)
        self.time += time() - t0

    def start(self):
        self.log.info("RedisListenConsumer started")

        self.register(SUBSCRIBER_NAME)
        while True:
            try:
                count = self.subscriber()            
            except NoSubscriberNameSetException as e:
                self.log.error("RedisListenConsumer has no subscriber name set.")
                return
            except WriteFailException as e:
                self.log.error("RedisListenConsumer failed to write to Postgres.")
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
    rc = RedisConsumer(r,config.SQLALCHEMY_DATABASE_URI)
    rc.start()
