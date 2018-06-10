""" This script runs perpetually and performs BigQuery jobs
like deleting users, calculating statistics from jobs
in the relevant RabbitMQ queue.
"""

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2017 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import listenbrainz.db.stats as db_stats
import listenbrainz.stats.user as stats_user
import logging
import pika
import time
import ujson

from listenbrainz import bigquery, db, stats, utils
from listenbrainz.bigquery.user import delete_user
from listenbrainz.stats.utils import construct_stats_queue_key
from listenbrainz.webserver import create_app

class BigQueryJobRunner:
    def __init__(self):
        self.app = create_app(debug=True) # creating a flask app for config values

        self.log = logging.getLogger(__name__)
        logging.basicConfig()
        self.log.setLevel(logging.INFO)


    def init_rabbitmq_connection(self):
        """ Initializes the connection to RabbitMQ.

        Note: this is a blocking function which keeps retrying if it fails
        to connect to RabbitMQ
        """
        self.connection = utils.connect_to_rabbitmq(
            username=self.app.config['RABBITMQ_USERNAME'],
            password=self.app.config['RABBITMQ_PASSWORD'],
            host=self.app.config['RABBITMQ_HOST'],
            port=self.app.config['RABBITMQ_PORT'],
            virtual_host=self.app.config['RABBITMQ_VHOST'],
            error_logger=self.log.error,
        )


    def callback(self, ch, method, properties, body):
        """ Handle the data received from the queue and work accordingly.
        """
        data = ujson.loads(body)

        job_type = data.get('type', '')
        if job_type == 'user':
            done = self.calculate_stats_for_user(data)
            if done:
                self.redis.set(construct_stats_queue_key(data['musicbrainz_id']), 'done')
        elif job_type == 'delete.user':
            self.log.info('Deleting user %s from BigQuery', data['musicbrainz_id'])
            delete_user(self.bigquery, data['musicbrainz_id'])
            self.log.info('Deletion complete!')
        else:
            self.log.info('Cannot recognize the type of entity in queue, ignoring...')
            return

        while True:
            try:
                self.incoming_ch.basic_ack(delivery_tag=method.delivery_tag)
                break
            except pika.exceptions.ConnectionClosed:
                self.init_rabbitmq_connection()


    def calculate_stats_for_user(self, user):
        """ Calculate statistics for specified user.

        Args:
            user: a dict which should contain the `id` and `musicbrainz_id` keys

        Returns:
            bool value specifying if user's stats were calculated or not.
        """
        try:
            user = {
                'id': user['id'],
                'musicbrainz_id': user['musicbrainz_id']
            }
        except KeyError:
            self.log.error('Invalid user data sent into queue, ignoring...')
            return False


        # if this user already has recent stats, ignore
        if db_stats.valid_stats_exist(user['id']):
            self.log.info('Stats already exist for user %s, moving on!', user['musicbrainz_id'])
            return False

        try:
            self.log.info('Calculating statistics for user %s...', user['musicbrainz_id'])
            recordings = stats_user.get_top_recordings(self.bigquery, user['musicbrainz_id'])
            self.log.info('Top recordings for user %s done!', user['musicbrainz_id'])

            artists = stats_user.get_top_artists(self.bigquery, user['musicbrainz_id'])
            self.log.info('Top artists for user %s done!', user['musicbrainz_id'])

            releases = stats_user.get_top_releases(self.bigquery, user['musicbrainz_id'])
            self.log.info('Top releases for user %s done!', user['musicbrainz_id'])

            artist_count = stats_user.get_artist_count(self.bigquery, user['musicbrainz_id'])
            self.log.info('Artist count for user %s done!', user['musicbrainz_id'])

        except Exception as e:
            self.log.error('Unable to calculate stats for user %s. :(', user['musicbrainz_id'])
            self.log.error('Error: %s', str(e))
            self.log.error('Giving up for now...')
            raise

        self.log.info('Inserting calculated stats for user %s into db', user['musicbrainz_id'])
        while True:
            try:
                db_stats.insert_user_stats(
                    user_id=user['id'],
                    artists=artists,
                    recordings=recordings,
                    releases=releases,
                    artist_count=artist_count
                )
                self.log.info('Stats calculation for user %s done!', user['musicbrainz_id'])
                break

            except Exception as e:
                self.log.error('Unable to insert calculated stats into db for user %s', user['musicbrainz_id'])
                self.log.error('Error: %s', str(e))
                self.log.error('Going to sleep and trying again...')
                time.sleep(3)

        return True


    def start(self):
        """ Starts the job runner. This should run perpetually,
            monitor the bigquery jobs rabbitmq queue and perform tasks for
            entries in the queue.
        """

        # if no bigquery support, sleep
        if not self.app.config['WRITE_TO_BIGQUERY']:
            while True:
                time.sleep(10000)

        self.log.info('Connecting to Google BigQuery...')
        self.bigquery = bigquery.create_bigquery_object()
        self.log.info('Connected!')

        self.log.info('Connecting to database...')
        db.init_db_connection(self.app.config['SQLALCHEMY_DATABASE_URI'])
        self.log.info('Connected!')

        self.log.info('Connecting to redis...')
        self.redis = utils.connect_to_redis(host=self.app.config['REDIS_HOST'], port=self.app.config['REDIS_PORT'], log=self.log.error)
        self.log.info('Connected!')

        while True:
            self.init_rabbitmq_connection()
            self.incoming_ch = utils.create_channel_to_consume(
                connection=self.connection,
                exchange=self.app.config['BIGQUERY_EXCHANGE'],
                queue=self.app.config['BIGQUERY_QUEUE'],
                callback_function=self.callback,
            )
            self.log.info('Stats calculator started!')
            try:
                self.incoming_ch.start_consuming()
            except pika.exceptions.ConnectionClosed:
                self.log.info("Connection to rabbitmq closed. Re-opening.")
                self.connection = None
                continue

            self.connection.close()


if __name__ == '__main__':
    jr = BigQueryJobRunner()
    jr.start()
