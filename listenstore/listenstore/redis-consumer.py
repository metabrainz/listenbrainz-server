#!/usr/bin/env python

import ujson
import logging
from listenstore.listenstore import Listen
from time import time, sleep
from webserver.redis_connection import _redis

BATCH_SIZE = 1000
REPORT_FREQUENCY = 10000
NO_ITEM_DELAY = .1   # in seconds
BATCH_TIMEOUT = 1    # in seconds

# TODO: Add support for now playing

class KafkaConsumer(object):
    def __init__(self, conf):
        self.log = logging.getLogger(__name__)
        self.total_inserts = 0
        self.inserts = 0
        self.listenstore = None


    def start_listens(self, listenstore):
        self.listenstore = listenstore
        return self.start()


    def start(self):
        self.log.info("RedisListenConsumer started")

        r = _redis

        while True:
            listens = []
            t0 = time()

            while True:
                listen = r.rpoplpush("listens", "listens-pending")
                if not listen:
                    sleep(NO_ITEM_DELAY)

                if time() - t0 > BATCH_TIMEOUT:
                    break

            if not listens:
                continue

            broken = True
            while broken:
                try:
                    self.listenstore.insert_batch(listens)
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
                self.log.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows. last offset: %d" % \
                    (self.inserts, t1 - t0, self.inserts / (t1 - t0), self.total_inserts, last_offset))
                self.inserts = 0
                t0 = 0
