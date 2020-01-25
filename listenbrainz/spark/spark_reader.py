
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
from listenbrainz.spark.handlers import handle_user_artist, handle_user_release, handle_user_track
import sqlalchemy

class SparkReader:
    def __init__(self):
        self.app = create_app() # creating a flask app for config values and logging to Sentry

    def get_response_handler(self, response_type):
        response_handler_map = {
            'user_artist': handle_user_artist,
            'user_release': handle_user_release,
            'user_track': handle_user_track,
        }
        return response_handler_map[response_type]


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

    def process_response(self, response):
        try:
            response_type = response['type']
            data = response.get('data', {})
        except KeyError:
            current_app.logger.error('Bad response sent to spark_reader: %s', json.dumps(request), exc_info=True)
            return

        try:
            response_handler = get_response_handler(response_type)
        except Exception:
            current_app.logger.error('Unknown response type: %s, doing nothing.', response_type, exc_info=True)
            return

        try:
            response_handler(data)
        except Exception as e:
            current_app.logger.error('Error in the response handler: %s', str(e), exc_info=True)
            return


    def callback(self, ch, method, properties, body):
        """ Handle the data received from the queue and
            insert into the database accordingly.
        """
        response = ujson.loads(body)
        self.process_response(response)
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
                    exchange=current_app.config['SPARK_RESULT_EXCHANGE'],
                    queue=current_app.config['SPARK_RESULT_QUEUE'],
                    callback_function=self.callback,
                )
                current_app.logger.info('Spark consumer started!')
                try:
                    self.incoming_ch.start_consuming()
                except pika.exceptions.ConnectionClosed:
                    current_app.logger.warning("Connection to rabbitmq closed. Re-opening.")
                    self.connection = None
                    continue

                self.connection.close()


if __name__ == '__main__':
    sr = SparkReader()
    sr.start()

