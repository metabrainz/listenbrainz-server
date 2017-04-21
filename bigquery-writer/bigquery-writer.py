#!/usr/bin/env python
import sys
import os
import ujson
import logging
import pika
from datetime import datetime
from time import time, sleep
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from listen import Listen
import config
from redis import Redis
from redis_keys import UNIQUE_QUEUE_SIZE_KEY

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

REPORT_FREQUENCY = 5000
APP_CREDENTIALS_FILE = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

# TODO:
#   Big query hardcoded data set ids

class BigQueryWriter(object):
    def __init__(self):
        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.log.setLevel(logging.INFO)

        self.redis = None
        self.connection = None
        self.channel = None

        self.total_inserts = 0
        self.inserts = 0
        self.time = 0

    def connect_to_rabbitmq(self):
        while True:
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=config.RABBITMQ_HOST, port=config.RABBITMQ_PORT))
                break
            except Exception as e:
                self.log.error("Cannot connect to rabbitmq: %s, sleeping 2 seconds")
                sleep(2)


    @staticmethod
    def static_callback(ch, method, properties, body, obj):
        return obj.callback(ch, method, properties, body)


    def callback(self, ch, method, properties, body):

        listens = ujson.loads(body)
        count = len(listens)

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

                'release_msid' : meta['additional_info'].get('release_msid', ''),
                'release_name' : meta['additional_info'].get('release_name', ''),
                'release_mbid' : meta['additional_info'].get('release_mbid', ''),

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
        while True:
            try:
                t0 = time()
                ret = self.bigquery.tabledata().insertAll(
                    projectId="listenbrainz",
                    datasetId="listenbrainz_test",
                    tableId="listen",
                    body=body).execute(num_retries=5)
                self.time += time() - t0
                break

            except HttpError as e:
                self.log.error("Submit to BigQuery failed: %s. Sleeping 2 seconds." % str(e))
            except Exception as e:
                self.log.error("Unknown exception on submit to BigQuery failed: %s. Sleeping 2 seconds." % str(e))
                if DUMP_JSON_WITH_ERRORS:
                    self.log.error(json.dumps(body, indent=3))

            sleep(2)


        while True:
            try:
                self.channel.basic_ack(delivery_tag = method.delivery_tag)
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()

        self.redis.decr(UNIQUE_QUEUE_SIZE_KEY, count)

        # Clear the start time, since we've cleaned out the batch
        batch_start_time = 0

        self.log.info("inserted %d listens." % count)

        # collect and occasionally print some stats
        self.inserts += count
        if self.inserts >= REPORT_FREQUENCY:
            self.total_inserts += self.inserts
            if self.time > 0:
                self.log.info("Inserted %d rows in %.1fs (%.2f listens/sec). Total %d rows." % \
                    (self.inserts, self.time, count / self.time, self.total_inserts))
            self.inserts = 0
            self.time = 0

        return True

    def start(self):
        self.log.info("biqquer-writer init")

        if not hasattr(config, "REDIS_HOST"):
            self.log.error("Redis service not defined. Sleeping 2 seconds and exiting.")
            sleep(2)
            return

        if not hasattr(config, "RABBITMQ_HOST"):
            self.log.error("RabbitMQ service not defined. Sleeping 2 seconds and exiting.")
            sleep(2)
            return

        # if we're not supposed to run, just sleep
        if not config.WRITE_TO_BIGQUERY:
            sleep(66666)
            return

        if not APP_CREDENTIALS_FILE:
            self.log.error("BiqQueryWriter not started, the GOOGLE_APPLICATION_CREDENTIALS env var is not defined.")
            sleep(1000)
            return

        if not os.path.exists(APP_CREDENTIALS_FILE):
            self.log.error("BiqQueryWriter not started, %s is missing." % APP_CREDENTIALS_FILE)
            sleep(1000)
            return

        credentials = GoogleCredentials.get_application_default()
        self.bigquery = discovery.build('bigquery', 'v2', credentials=credentials)

        while True:
            try:
                self.redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)
                break
            except Exception as err:
                self.log.error("Cannot connect to redis: %s. Sleeping 2 seconds and trying again." % str(err))
                sleep(2)

        while True:
            self.connect_to_rabbitmq()
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange='unique', type='fanout')
            self.channel.queue_declare('unique', durable=True)
            self.channel.queue_bind(exchange='unique', queue='unique')
            self.channel.basic_consume(lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self), queue='unique')

            self.log.info("bigquery-writer started")
            try:
                self.channel.start_consuming()
            except pika.exceptions.ConnectionClosed:
                self.log.info("Connection to rabbitmq closed. Re-opening.")
                self.connection = None
                self.channel = None
                continue

            self.connection.close()


if __name__ == "__main__":
    bq = BigQueryWriter()
    bq.start()
