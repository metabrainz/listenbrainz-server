#!/usr/bin/env python3

import sys
import os
import ujson
import json
import logging
import pika
from time import time, sleep
from redis import Redis

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from listenbrainz.bigquery import create_bigquery_object
from listenbrainz.bigquery import NoCredentialsVariableException, NoCredentialsFileException
from oauth2client.client import GoogleCredentials

from listenbrainz import default_config as config
try:
    from listenbrainz import custom_config as config
except ImportError:
    pass

REPORT_FREQUENCY = 5000
ERROR_RETRY_DELAY = 3 # number of seconds to wait until retrying an operation
DUMP_JSON_WITH_ERRORS = True

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
                credentials = pika.PlainCredentials(config.RABBITMQ_USERNAME, config.RABBITMQ_PASSWORD)
                connection_parameters = pika.ConnectionParameters(
                        host=config.RABBITMQ_HOST,
                        port=config.RABBITMQ_PORT,
                        virtual_host=config.RABBITMQ_VHOST,
                        credentials=credentials
                    )
                self.connection = pika.BlockingConnection(connection_parameters)
                break
            except Exception as e:
                self.log.error("Cannot connect to rabbitmq: %s, retrying in 3 seconds" % str(e))
                sleep(ERROR_RETRY_DELAY)


    @staticmethod
    def static_callback(ch, method, properties, body, obj):
        return obj.callback(ch, method, body)


    def callback(self, ch, method, body):

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
                'insertId': "%s-%s-%s" % (listen['user_name'], listen['listened_at'], listen['recording_msid'])
            })

        body = { 'rows' : bq_data }
        while True:
            try:
                t0 = time()
                ret = self.bigquery.tabledata().insertAll(
                    projectId=config.BIGQUERY_PROJECT_ID,
                    datasetId=config.BIGQUERY_DATASET_ID,
                    tableId=config.BIGQUERY_TABLE_ID,
                    body=body).execute(num_retries=5)
                self.time += time() - t0
                break

            except HttpError as e:
                self.log.error("Submit to BigQuery failed: %s. Retrying in 3 seconds." % str(e))
            except Exception as e:
                self.log.error("Unknown exception on submit to BigQuery failed: %s. Retrying in 3 seconds." % str(e))
                if DUMP_JSON_WITH_ERRORS:
                    self.log.error(json.dumps(body, indent=3))

            sleep(ERROR_RETRY_DELAY)


        while True:
            try:
                self.channel.basic_ack(delivery_tag = method.delivery_tag)
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()

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
            self.log.error("Redis service not defined. Sleeping 3 seconds and exiting.")
            sleep(ERROR_RETRY_DELAY)
            return

        if not hasattr(config, "RABBITMQ_HOST"):
            self.log.error("RabbitMQ service not defined. Sleeping 3 seconds and exiting.")
            sleep(ERROR_RETRY_DELAY)
            return

        # if we're not supposed to run, just sleep
        if not config.WRITE_TO_BIGQUERY:
            sleep(66666)
            return

        try:
            self.bigquery = create_bigquery_object()
        except (NoCredentialsFileException, NoCredentialsVariableException):
            self.log.error("Credential File not present or invalid! Sleeping...")
            sleep(1000)

        while True:
            try:
                self.redis = Redis(host=config.REDIS_HOST, port=config.REDIS_PORT)
                self.redis.ping()
                break
            except Exception as err:
                self.log.error("Cannot connect to redis: %s. Retrying in 3 seconds and trying again." % str(err))
                sleep(ERROR_RETRY_DELAY)

        while True:
            self.connect_to_rabbitmq()
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange=config.UNIQUE_EXCHANGE, type='fanout')
            self.channel.queue_declare(config.UNIQUE_QUEUE, durable=True)
            self.channel.queue_bind(exchange=config.UNIQUE_EXCHANGE, queue=config.UNIQUE_QUEUE)
            self.channel.basic_consume(
                lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self),
                queue=config.UNIQUE_QUEUE,
            )

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
