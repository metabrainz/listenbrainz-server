#!/usr/bin/env python3

import json
import listenbrainz.utils as utils
import logging
import os
import pika
import sys
import ujson
import time

from listenbrainz.webserver import create_app

from flask import current_app
from googleapiclient import discovery
from googleapiclient.errors import HttpError
from listenbrainz.listen_writer import ListenWriter
from listenbrainz.bigquery import create_bigquery_object
from listenbrainz.bigquery import NoCredentialsVariableException, NoCredentialsFileException
from oauth2client.client import GoogleCredentials
from redis import Redis
from time import time, sleep



SUBMIT_CHUNK_SIZE = 1000 # the number of listens to send to BQ in one batch

# NOTE: this MUST be greater than or equal to the maximum number of listens sent to us in one
# RabbitMQ batch, otherwise BigQueryWriter will submit a partial batch and send an ack for
# the batch.
assert(SUBMIT_CHUNK_SIZE >= 50)

PREFETCH_COUNT = 20    # the number of RabbitMQ batches to prefetch
FLUSH_LISTENS_TIME = 3 # the number of seconds to wait before flushing all listens in queue to BQ


class BigQueryWriter(ListenWriter):
    def __init__(self):
        super().__init__()

        self.channel = None

        self.bq_data = []
        self.delivery_tags = []

        self.timer_id = None # keeps track of the timer added to flush listens



    def submit_data(self):
        """ Submits the data in self.bq_data to Google BigQuery and
            acknowledges the appropriate delivery tags.
        """

        if len(self.bq_data) == 0:
            return

        assert(len(self.bq_data) > 0)
        assert(len(self.delivery_tags) > 0)

        t0 = time()

        # convert the data to BQ format and send
        body = {
            'rows': self.bq_data,
        }
        while True:
            try:
                ret = self.bigquery.tabledata().insertAll(
                    projectId=current_app.config['BIGQUERY_PROJECT_ID'],
                    datasetId=current_app.config['BIGQUERY_DATASET_ID'],
                    tableId=current_app.config['BIGQUERY_TABLE_ID'],
                    body=body).execute(num_retries=5)
                break
            except HttpError as e:
                current_app.logger.error("Submit to BigQuery failed: %s. Retrying in 3 seconds. Data: %s", str(e), json.dumps(body, indent=3), exc_info=True)
            except Exception as e:
                current_app.logger.error("Exception while submitting data to BigQuery: %s. Retrying in 3 seconds. Data: %s", str(e), json.dumps(body, indent=3), exc_info=True)

            sleep(self.ERROR_RETRY_DELAY)


        # now that data has been sent, acknowledge all delivery tags for listens in
        # the current batch
        latest_delivery_tag = max(self.delivery_tags)
        while True:
            try:
                self.channel.basic_ack(delivery_tag=latest_delivery_tag, multiple=True)
                break
            except pika.exceptions.ConnectionClosed:
                self.connect_to_rabbitmq()

            sleep(self.ERROR_RETRY_DELAY)

        # collect and occasionally print some stats
        time_taken = time() - t0
        self.total_inserts += len(self.bq_data)
        current_app.logger.info(
            'Inserted %d listens in %.1fs (%.2f listens/sec). Total %d rows.',
            len(self.bq_data),
            time_taken,
            len(self.bq_data) / time_taken,
            self.total_inserts
        )

        # reset back to normal
        self.bq_data = []
        self.delivery_tags = []


    def convert_to_bigquery_payload(self, listens):
        """ Converts a list of listens to Google BigQuery rows.

        Args:
            listens (list): a list of listens
            Each listen must be of the following format:
                {
                    'user_name': MusicBrainz ID of the user,
                    'listened_at': unix timestamp of the listen,
                    'recording_msid': the MessyBrainz ID of the recording,
                    'track_metadata': {
                        'artist_msid': MessyBrainz ID of the artist,
                        'artist_name': Name of the artist,
                        'track_name': the name of the track,
                    }
                }

        Returns:
            payload (list): a list of dictionaries, each representing a row that can
                            be submitted to Google BigQuery

            Each row is of the following format:
                {
                    'insertId': the unique insert ID of the row, this is used by BigQuery to ensure
                                rows don't get lost,
                    'json': {
                        value for each of the rows in the BigQuery schema
                    }
                }
        """
        payload = []
        for listen in listens:
            meta = listen['track_metadata']
            row = {
                'user_name' : listen['user_name'],
                'listened_at' : listen['listened_at'],

                'artist_msid' : meta['additional_info']['artist_msid'],
                'artist_name' : meta['artist_name'],
                'artist_mbids' : ','.join(meta['additional_info'].get('artist_mbids', [])),

                'release_msid' : meta['additional_info'].get('release_msid', ''),
                'release_name' : meta.get('release_name', ''),
                'release_mbid' : meta['additional_info'].get('release_mbid', ''),

                'track_name' : meta['track_name'],
                'recording_msid' : listen['recording_msid'],
                'recording_mbid' : meta['additional_info'].get('recording_mbid', ''),

                'tags' : ','.join(meta['additional_info'].get('tags', [])),
            }
            payload.append({
                'json': row,
                'insertId': '%s-%s-%s' % (listen['user_name'], listen['listened_at'], listen['recording_msid'])
            })
        return payload


    def callback(self, ch, method, properties, body):

        # if some timeout exists, remove it as we'll add a new one
        # before this method exits
        if self.timer_id is not None:
            ch.connection.remove_timeout(self.timer_id)
            self.timer_id = None

        listens = ujson.loads(body)
        count = len(listens)

        # if adding this batch pushes us over the line, send this batch before
        # adding new listens to queue
        if len(self.bq_data) + count > SUBMIT_CHUNK_SIZE:
            self.submit_data()

        # now add current listens to the queue
        payload = self.convert_to_bigquery_payload(listens)
        self.bq_data.extend(payload)
        self.delivery_tags.append(method.delivery_tag)

        # if we won't get any new messages until we ack these, submit data
        if len(self.delivery_tags) == PREFETCH_COUNT:
            self.submit_data()

        # add a timeout that makes sure that the listens in the queue get submitted
        # after some time
        self.timer_id = ch.connection.add_timeout(FLUSH_LISTENS_TIME, self.submit_data)

        return True


    def start(self):
        app = create_app()
        with app.app_context():
            current_app.logger.info("bigquery-writer init")

            self._verify_hosts_in_config()

            # if we're not supposed to run, just sleep
            if not current_app.config['WRITE_TO_BIGQUERY']:
                sleep(66666)
                return

            try:
                self.bigquery = create_bigquery_object()
            except NoCredentialsFileException as e:
                current_app.logger.critical("BigQuery credential file not present! Sleeping...")
                sleep(100000)
            except NoCredentialsVariableException as e:
                current_app.logger.critical("BigQuery credentials environment variable not set!")
                sleep(100000)

            while True:
                try:
                    self.redis = Redis(
                        host=current_app.config['REDIS_HOST'],
                        port=current_app.config['REDIS_PORT'],
                    )
                    self.redis.ping()
                    break
                except Exception as err:
                    current_app.logger.warn("Cannot connect to redis: %s. Retrying in 3 seconds and trying again." % str(err), exc_info=True)
                    sleep(self.ERROR_RETRY_DELAY)

            while True:
                self.connect_to_rabbitmq()
                self.channel = self.connection.channel()
                self.channel.exchange_declare(exchange=current_app.config['UNIQUE_EXCHANGE'], exchange_type='fanout')
                self.channel.queue_declare(current_app.config['UNIQUE_QUEUE'], durable=True)
                self.channel.queue_bind(exchange=current_app.config['UNIQUE_EXCHANGE'], queue=current_app.config['UNIQUE_QUEUE'])
                self.channel.basic_consume(
                    lambda ch, method, properties, body: self.static_callback(ch, method, properties, body, obj=self),
                    queue=current_app.config['UNIQUE_QUEUE'],
                )
                self.channel.basic_qos(prefetch_count=PREFETCH_COUNT)

                current_app.logger.info("bigquery-writer started")
                try:
                    self.channel.start_consuming()
                except pika.exceptions.ConnectionClosed:
                    current_app.logger.warn("Connection to rabbitmq closed. Re-opening.")
                    self.connection = None
                    self.channel = None
                    continue

                self.connection.close()


if __name__ == "__main__":
    bq = BigQueryWriter()
    bq.start()
