#!/usr/bin/env python

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from redis import Redis
from redis_keys import REDIS_LISTEN_JSON, REDIS_LISTEN_JSON_REFCOUNT, REDIS_LISTEN_CONSUMER_IDS, \
    REDIS_LISTEN_CONSUMERS
import config
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

import ujson
import logging
from listen import Listen
from time import time, sleep

BATCH_SIZE = 1000
REPORT_FREQUENCY = 5000
BATCH_TIMEOUT = 5      # in seconds. Don't let a listen get older than this before writing
REQUEST_TIMEOUT = 1    # in seconds. Wait this long to get a listen from redis

CONSUMER_NAME = "bq"
APP_CREDENTIALS_FILE = "big-query-credentials.json"

# Things left to do
#   Redis persistence
#   Use the two lists model in order to not lose any items in case of restart
#   Figure out where the bigquery data actuall ends up. :)

class BigQueryWriter(object):
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

        self.log.debug("BiqQueryWriter started")
        if not config.WRITE_TO_BIGQUERY or not os.path.exists(APP_CREDENTIALS_FILE):
            if not os.path.exists(APP_CREDENTIALS_FILE):
                self.log.error("BiqQueryWriter not started, big-query-credentials.json is missing.")

            # Rather than exit, just loop, otherwise the container will get 
            # restarted over and over
            while True:
                sleep(100)

        self.log.info("BiqQueryWriter started")

        credentials = GoogleCredentials.get_application_default()
        bigquery = discovery.build('bigquery', 'v2', credentials=credentials)

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
            bq_data = []

            # REMOVE ME
            import json
            listens = listens[0:1]
            for listen in listens:
                self.log.error(json.dumps(listen, indent=3))
                row = {
                    'user_name' : listen.user_id,
                    'listened_at' : listen.timestamp,

                    'artist_msid' : listen.artist_msid,
                    'artist_name' : listen.data.get('artist_name', ''),
                    'artist_mbids' : ",".join(listen.data.get('artist_mbids', [])),

                    'album_msid' : listen.album_msid,
                    'album_name' : listen.data.get('release_name', ''),
                    'album_mbid' : listen.data.get('release_mbid', ''),

                    'track_name' : listen.data.get('track_name', ''),
                    'recording_msid' : listen.recording_msid,
                    'recording_mbid' : listen.data.get('recording_mbid', ''),

                    'tags' : ",".join(listen.data.get('tags', [])),
                }
                bq_data.append({
                    'json': row, 
                    'insertId': "%s-%s" % (listen.user_id, listen.timestamp)
                })

            body = { 'rows' : bq_data }
            self.log.error(json.dumps(body, indent=3))
            try:
                t0 = time()
                ret = bigquery.tabledata().insertAll(
                    projectId="listenbrainz",
                    datasetId="listenbrainz_test",
                    tableId="listen",
                    body=body).execute(num_retries=5)
                self.log.error(json.dumps(ret, indent=3))
                self.time += time() - t0
                self.log.error("Submitted %d rows" % len(bq_data))
            except HttpError as e:
                self.log.error("Submit to BigQuery failed: " + str(e))

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
    rc = BigQueryWriter()
    rc.start(config.REDIS_HOST)
