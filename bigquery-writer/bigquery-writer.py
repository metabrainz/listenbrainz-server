#!/usr/bin/env python
import sys
import os
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from redis import Redis
from redis_pubsub import RedisPubSubSubscriber, RedisPubSubPublisher, NoSubscriberNameSetException, WriteFailException
import ujson
import logging
from listen import Listen
from time import time, sleep
import config

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

REPORT_FREQUENCY = 5000
SUBSCRIBER_NAME = "bq"
KEYSPACE_NAME_INCOMING = "ilisten"
KEYSPACE_NAME_UNIQUE = "ulisten"
APP_CREDENTIALS_FILE = "bigquery-credentials.json"

# Things left to do
#   Redis persistence
#   Influx listenstore functions
#   Add unit tests for pubsub object, incoing and unique queue
#   Bring non-prod docker-compose up to date with prod one


class BigQueryWriterSubscriber(RedisPubSubSubscriber):
    def __init__(self, redis):
        RedisPubSubSubscriber.__init__(self, redis, KEYSPACE_NAME_UNIQUE)

        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

    def write(self, listens):

        # We've collected listens to write, now write them
        bq_data = []

        for listen in listens:
            meta = listen['track_metadata']
            row = {
                'user_name' : listen['user_name'],
                'listened_at' : listen['listened_at'],

                'artist_msid' : meta['additional_info']['artist_msid'],
                'artist_name' : meta['artist_name'],
                'artist_mbids' : ",".join(meta['additional_info'].get('artist_mbids', [])),

                'album_msid' : meta['additional_info'].get('album_msid', ''),
                'album_name' : meta['additional_info'].get('release_name', ''),
                'album_mbid' : meta['additional_info'].get('release_mbid', ''),

                'track_name' : meta['track_name'],
                'recording_msid' : listen['recording_msid'],
                'recording_mbid' : meta['additional_info'].get('recording_mbid', ''),

                'tags' : ",".join(meta['additional_info'].get('tags', [])),
            }
            bq_data.append({
                'json': row, 
                'insertId': "%s-%s" % (listen['user_name'], listen['listened_at'])
            })

        body = { 'rows' : bq_data }
        try:
            t0 = time()
            ret = self.bigquery.tabledata().insertAll(
                projectId="listenbrainz",
                datasetId="listenbrainz_test",
                tableId="listen",
                body=body).execute(num_retries=5)
            self.time += time() - t0
        except HttpError as e:
            self.log.error("Submit to BigQuery failed: " + str(e))
            self.log.error(json.dumps(body, indent=3))

        # Clear the start time, since we've cleaned out the batch
        batch_start_time = 0

        return True

    def start(self):
        self.log.info("BigQueryWriterSubscriber started")

        if not config.WRITE_TO_BIGQUERY or not os.path.exists(APP_CREDENTIALS_FILE):
            if not os.path.exists(APP_CREDENTIALS_FILE):
                self.log.error("BiqQueryWriter not started, big-query-credentials.json is missing.")

            # Rather than exit, just loop, otherwise the container will get 
            # restarted over and over
                sleep(100)

        credentials = GoogleCredentials.get_application_default()
        self.bigquery = discovery.build('bigquery', 'v2', credentials=credentials)

        self.register(SUBSCRIBER_NAME)
        while True:
            try:
                count = self.subscriber()            
            except NoSubscriberNameSetException as e:
                self.log.error("BigQueryWriterSubscriber has no subscriber name set.")
                return
            except WriteFailException as e:
                self.log.error("BigQueryWriterSubscriber failed to write: %s" % str(e))
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
    r = Redis(config.REDIS_HOST)
    bq = BigQueryWriterSubscriber(r)
    bq.start()
