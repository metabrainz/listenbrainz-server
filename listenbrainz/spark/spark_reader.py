import json
import time

import ujson
from kombu import Connection, Message, Consumer, Exchange, Queue
from kombu.mixins import ConsumerMixin

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
                                         cf_recording_recommendations_complete,
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
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app

import eventlet
eventlet.monkey_patch()


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
    'cf_recommendations_recording_mail': cf_recording_recommendations_complete,
    'similar_users': handle_similar_users,
    'similar_users_year_end': handle_similar_users_year_end,
    'year_in_music_top_stats': handle_top_stats,
    'year_in_music_listens_per_day': handle_listens_per_day,
    'year_in_music_listen_count': handle_yearly_listen_counts
}

RABBITMQ_HEARTBEAT_TIME = 60 * 60  # 1 hour, in seconds


class SparkReader(ConsumerMixin):

    def __init__(self, app):
        self.app = app
        self.connection = None
        self.spark_result_exchange = Exchange(app.config["SPARK_RESULT_EXCHANGE"], "fanout", durable=True)
        self.spark_result_queue = Queue(app.config["SPARK_RESULT_QUEUE"], exchange=self.spark_result_exchange,
                                        durable=True)
        
    def get_consumers(self, _, channel):
        return [Consumer(channel, queues=[self.spark_result_queue], on_message=lambda msg: self.callback(msg))]

    def get_response_handler(self, response_type):
        return response_handler_map[response_type]

    def init_rabbitmq_connection(self):
        self.connection = Connection(
            hostname=self.app.config["RABBITMQ_HOST"],
            userid=self.app.config["RABBITMQ_USERNAME"],
            port=self.app.config["RABBITMQ_PORT"],
            password=self.app.config["RABBITMQ_PASSWORD"],
            virtual_host=self.app.config["RABBITMQ_VHOST"],
            transport_options={"client_properties": {"connection_name": get_fallback_connection_name()}}
        )

    def process_response(self, response):
        try:
            response_type = response['type']
        except KeyError:
            self.app.logger.error("Bad response sent to spark_reader: %s", json.dumps(response, indent=4),
                                  exc_info=True)
            return
        self.app.logger.info("Received message for %s", response_type)
        try:
            response_handler = self.get_response_handler(response_type)
        except Exception:
            self.app.logger.error("Unknown response type: %s, doing nothing.", response_type, exc_info=True)
            return

        try:
            response_handler(response)
        except Exception:
            self.app.logger.error("Error in the spark reader response handler: data: %s",
                                  json.dumps(response, indent=4), exc_info=True)
            return

    def callback(self, message: Message):
        """ Handle the data received from the queue and
            insert into the database accordingly.
        """
        self.app.logger.debug("Received a message, processing...")
        response = ujson.loads(message.body)
        self.process_response(response)
        message.ack()
        self.app.logger.debug("Done!")

    def start(self):
        """ initiates RabbitMQ connection and starts consuming from the queue
        """
        with self.app.app_context():
            while True:
                try:
                    self.app.logger.info('Spark consumer has started!')
                    self.init_rabbitmq_connection()
                    self.run()
                except KeyboardInterrupt:
                    self.app.logger.error("Keyboard interrupt!")
                    break
                except Exception:
                    self.app.logger.error("Error in PlayerWriter:", exc_info=True)
                    time.sleep(3)


if __name__ == '__main__':
    sr = SparkReader(create_app())
    sr.start()
