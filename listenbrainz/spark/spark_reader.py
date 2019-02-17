import json
import logging
import pika
import time
import ujson

from flask import current_app
from listenbrainz import utils
from listenbrainz.db import user as db_user, stats as db_stats
from listenbrainz.webserver import create_app
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz import config
import sqlalchemy

class SparkReader:
    def __init__(self):
        self.app = create_app() # creating a flask app for config values and logging to Sentry


    def init_rabbitmq_connection(self):
        """ Initializes the connection to RabbitMQ.

        Note: this is a blocking function which keeps retrying if it fails
        to connect to RabbitMQ
        """
        self.connection = utils.connect_to_rabbitmq(
            username=current_app.config['RABBITMQ_USERNAME'],
            password=current_app.config['RABBITMQ_PASSWORD'],
            host=current_app.config['RABBITMQ_HOST'],
            port=current_app.config['RABBITMQ_PORT'],
            virtual_host=current_app.config['RABBITMQ_VHOST'],
            error_logger=current_app.logger.error,
        )


    def callback(self, ch, method, properties, body):
        """ Handle the data received from the queue and works accordingly.
        """
        data = ujson.loads(body)
        user_name = next(iter(data[0]))
        user = db_user.get_by_mb_id(user_name)
        artists = data[0][user_name]['artists']['artist_stats']
        recordings = data[0][user_name]['recordings']
        releases = data[0][user_name]['releases']
        artist_count = data[0][user_name]['artists']['artist_count']
        db_stats.insert_user_stats(user['id'], artists, recordings, releases, artist_count)
        print ("data for {} published".format(user_name))

        while True:
            try:
                self.incoming_ch.basic_ack(delivery_tag=method.delivery_tag)
                break
            except pika.exceptions.ConnectionClosed:
                self.init_rabbitmq_connection()


    def start(self):
    	""" initiates RabbitMQ connection and starts consuming from the queue
    	"""

    	with self.app.app_context():

            while True:
                self.init_rabbitmq_connection()
                self.incoming_ch = utils.create_channel_to_consume(
                    connection=self.connection,
                    exchange=current_app.config['SPARK_EXCHANGE'],
                    queue=current_app.config['SPARK_QUEUE'],
                    callback_function=self.callback,
                )
                current_app.logger.info('Stats calculator started!')
                try:
                    print("consuming")
                    self.incoming_ch.start_consuming()
                except pika.exceptions.ConnectionClosed:
                    current_app.logger.warning("Connection to rabbitmq closed. Re-opening.")
                    self.connection = None
                    continue

                self.connection.close()


if __name__ == '__main__':
    sr = SparkReader()
    sr.start()