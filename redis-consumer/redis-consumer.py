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
REPORT_FREQUENCY = 5000
NO_ITEM_DELAY = .1   # in seconds
BATCH_TIMEOUT = 3    # in seconds

class RedisConsumer(object):
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

    def start(self, database_uri, redis_host):
        self.log.info("RedisListenConsumer started")

        r = Redis(redis_host)
        ls = PostgresListenStore({
          'SQLALCHEMY_DATABASE_URI': database_uri,
        })
        while True:
            listens = []
            t0 = time()

            # If there are some bits left in listens-peding, insert them!
            if r.llen("listens-pending") > 0:
                listens = r.lrange("listens-pending", 0, -1)
                submit = []
                for listen in listens:
                    data = ujson.loads(listen)
                    l = Listen().from_json(data)
                    if l.validate():
                        submit.append(l)

                # We've fetched them, now submit and if successful, clear the pending items
                try:
                    ls.insert_postgresql(submit)
                    r.ltrim("listens-pending", 1, 0)
                except ValueError:
                    pass

            # read new items from listens, adding to listens-pending.
            # keep doing this until we time out (no new ones) or we've reached our
            # batch size. Then write to db
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

            # We've collected stuff to write, now write it
            broken = True
            while broken:
                try:
                    t0 = time()
                    ls.insert_postgresql(listens)
                    self.time += time() - t0
                    broken = False

                except ValueError as e:
                    self.log.error("Cannot insert listens: %s" % unicode(e))
                    broken = False

            # clear the listens-pending list
            r.ltrim("listens-pending", 1, 0)

            # clear the now playing list -- at some point we'll want to consume them in 
            # some other fashion, but for now, just nuke them.
            r.ltrim("playing_now", 1, 0)

            # collect and occasionally print some stats
            self.inserts += len(listens)
            if self.inserts >= REPORT_FREQUENCY:
                self.total_inserts += self.inserts
                self.log.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                    (self.inserts, self.time, self.inserts / self.time, self.total_inserts))
                self.inserts = 0
                self.time = 0

if __name__ == "__main__":
    rc = RedisConsumer()
    rc.start(config.SQLALCHEMY_DATABASE_URI, config.REDIS_HOST)
