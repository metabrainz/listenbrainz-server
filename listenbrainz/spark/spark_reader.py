import json
import logging
import time

from flask import current_app

import pika
import sqlalchemy
import ujson
from listenbrainz import utils
from listenbrainz.db import stats as db_stats
from listenbrainz.db import user as db_user
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.spark.handlers import (handle_candidate_sets,
                                         handle_dataframes,
                                         handle_dump_imported, handle_model,
                                         handle_recommendations,
                                         handle_user_daily_activity,
                                         handle_user_entity,
                                         handle_user_listening_activity,
                                         handle_sitewide_entity,
                                         notify_artist_relation_import,
                                         notify_mapping_import,
                                         handle_missing_musicbrainz_data,
                                         notify_cf_recording_recommendations_generation,
                                         handle_recording_discovery,
                                         handle_sitewide_listening_activity,
                                         handle_similar_users,
                                         handle_new_releases_of_top_artists,
                                         handle_most_prominent_color,
                                         handle_similar_users_year_end,
                                         handle_day_of_week,
                                         handle_most_listened_year,
                                         handle_top_stats,
                                         handle_listens_per_day,
                                         handle_yearly_listen_counts)
from listenbrainz.webserver import create_app

response_handler_map = {
    'user_entity': handle_user_entity,
    'user_listening_activity': handle_user_listening_activity,
    'user_daily_activity': handle_user_daily_activity,
    'sitewide_entity': handle_sitewide_entity,
    'sitewide_listening_activity': handle_sitewide_listening_activity,
    'new_releases_of_top_artists': handle_new_releases_of_top_artists,
    'most_prominent_color': handle_most_prominent_color,
    'day_of_week': handle_day_of_week,
    'most_listened_year': handle_most_listened_year,
    'import_full_dump': handle_dump_imported,
    'import_incremental_dump': handle_dump_imported,
    'cf_recommendations_recording_dataframes': handle_dataframes,
    'cf_recommendations_recording_model': handle_model,
    'cf_recommendations_recording_candidate_sets': handle_candidate_sets,
    'cf_recommendations_recording_recommendations': handle_recommendations,
    'import_mapping': notify_mapping_import,
    'import_artist_relation': notify_artist_relation_import,
    'missing_musicbrainz_data': handle_missing_musicbrainz_data,
    'cf_recommendations_recording_mail': notify_cf_recording_recommendations_generation,
    'recording_discovery': handle_recording_discovery,
    'similar_users': handle_similar_users,
    'similar_users_year_end': handle_similar_users_year_end,
    'year_in_music_top_stats': handle_top_stats,
    'year_in_music_listens_per_day': handle_listens_per_day,
    'year_in_music_listen_count': handle_yearly_listen_counts
}

RABBITMQ_HEARTBEAT_TIME = 60 * 60  # 1 hour, in seconds


class SparkReader:
    def __init__(self):
        self.app = create_app()  # creating a flask app for config values and logging to Sentry

    def get_response_handler(self, response_type):
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
            heartbeat=RABBITMQ_HEARTBEAT_TIME,
        )

    def process_response(self, response):
        try:
            response_type = response['type']
        except KeyError:
            current_app.logger.error("Bad response sent to spark_reader: %s", json.dumps(response, indent=4),
                                     exc_info=True)
            return
        current_app.logger.info("Received message for %s", response_type)
        try:
            response_handler = self.get_response_handler(response_type)
        except Exception:
            current_app.logger.error("Unknown response type: %s, doing nothing.", response_type,
                                     exc_info=True)
            return

        try:
            response_handler(response)
        except Exception:
            current_app.logger.error("Error in the spark reader response handler: data: %s",
                                     json.dumps(response, indent=4), exc_info=True)
            return

    def callback(self, ch, method, properties, body):
        """ Handle the data received from the queue and
            insert into the database accordingly.
        """
        current_app.logger.debug("Received a message, processing...")
        response = ujson.loads(body)
        self.process_response(response)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        current_app.logger.debug("Done!")

    def start(self):
        """ initiates RabbitMQ connection and starts consuming from the queue
        """

        with self.app.app_context():
            current_app.logger.info('Spark consumer has started!')
            while True:
                self.init_rabbitmq_connection()
                self.incoming_ch = utils.create_channel_to_consume(
                    connection=self.connection,
                    exchange=current_app.config['SPARK_RESULT_EXCHANGE'],
                    queue=current_app.config['SPARK_RESULT_QUEUE'],
                    callback_function=self.callback,
                    auto_ack=False,
                )
                current_app.logger.info('Spark consumer attempt to start consuming!')
                try:
                    self.incoming_ch.start_consuming()
                except pika.exceptions.ConnectionClosed:
                    current_app.logger.warning('Spark consumer pika connection closed!')
                    self.connection = None
                    continue

                self.connection.close()


if __name__ == '__main__':
    sr = SparkReader()
    sr.start()
