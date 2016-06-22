#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../listenstore"))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import config

import ujson
import logging
from listenstore.listenstore import Listen, PostgresListenStore
from time import time, sleep
from redis import Redis

BATCH_SIZE = 1000
REPORT_FREQUENCY = 2000
NO_ITEM_DELAY = .1   # in seconds
BATCH_TIMEOUT = 3    # in seconds

# TODO: Add support for now playing

class RedisConsumer(object):
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.total_inserts = 0
        self.inserts = 0

    def start(self, database_uri, redis_host):
        self.log.info("RedisListenConsumer started")

        r = Redis(redis_host)
        ls = PostgresListenStore({
          'SQLALCHEMY_DATABASE_URI': database_uri,
        })
        while True:
            listens = []
            t0 = time()

            # TODO: Check to make sure the list is empty when you arrive here

            while True:
                listen = r.rpoplpush("listens", "listens-pending")
                if listen:
                    data = ujson.loads(listen)
                    l = Listen().from_json(data)
                    if l.validate():
                        listens.append(l)
                    else:
                        self.log.error("invalid listen: " + str(l))
                    t0 = time()
                else:
                    sleep(NO_ITEM_DELAY)

                if time() - t0 > BATCH_TIMEOUT or len(listens) >= BATCH_SIZE:
                    break

            if not listens:
                continue
            self.log.info("read %d listens from redis" % len(listens))

            broken = True
            while broken:
                try:
                    ls.insert_postgresql(listens)
                    broken = False

                except ValueError as e:
                    self.log.error("Cannot insert listens: %s" % unicode(e))
                    broken = False

            # clear the listens-pending list
            r.ltrim("listens-pending", 1, 0)

            self.inserts += len(listens)
            if self.inserts >= REPORT_FREQUENCY:
                t1 = time()
                self.total_inserts += self.inserts
                self.log.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                    (self.inserts, t1 - t0, self.inserts / (t1 - t0), self.total_inserts))
                self.inserts = 0
                t0 = 0

if __name__ == "__main__":
    rc = RedisConsumer()
    rc.start(config.SQLALCHEMY_DATABASE_URI, config.REDIS_HOST)
