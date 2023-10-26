#!/usr/bin/env python3
import json
import time

import orjson
import sentry_sdk
from kombu import Connection, Message, Consumer, Exchange, Queue
from kombu.mixins import ConsumerMixin

from listenbrainz.db.popularity import RecordingPopularityDataset, ReleasePopularityDataset, \
    TopRecordingPopularityDataset, ArtistPopularityDataset, TopReleasePopularityDataset
from listenbrainz.db.similarity import SimilarRecordingsDataset, SimilarArtistsDataset
from listenbrainz.db.tags import TagsDataset
from listenbrainz.spark.handlers import (
    handle_candidate_sets,
    handle_dataframes,
    handle_dump_imported,
    handle_model,
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
    handle_yim_new_releases_of_top_artists,
    handle_yim_similar_users,
    handle_yim_day_of_week,
    handle_yim_most_listened_year,
    handle_yim_top_stats,
    handle_yim_listens_per_day,
    handle_yim_listen_counts,
    handle_fresh_releases,
    handle_entity_listener,
    handle_yim_listening_time,
    handle_new_artists_discovered_count,
    handle_yim_tracks_of_the_year_start,
    handle_yim_tracks_of_the_year_data,
    handle_yim_tracks_of_the_year_end,
    handle_yim_artist_map,
    handle_troi_playlists,
    handle_troi_playlists_end)
from listenbrainz.spark.spark_dataset import CouchDbDataset
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app


class SparkReader(ConsumerMixin):

    def __init__(self, app):
        self.app = app
        self.connection = None
        self.spark_result_exchange = Exchange(app.config["SPARK_RESULT_EXCHANGE"], "fanout", durable=False)
        self.spark_result_queue = Queue(app.config["SPARK_RESULT_QUEUE"], exchange=self.spark_result_exchange,
                                        durable=True)
        self.response_handlers = {}

    def register_handlers(self):
        datasets = [
            CouchDbDataset,
            SimilarRecordingsDataset,
            SimilarArtistsDataset,
            TagsDataset,
            RecordingPopularityDataset,
            ReleasePopularityDataset,
            ArtistPopularityDataset,
            TopRecordingPopularityDataset,
            TopReleasePopularityDataset,
        ]
        for dataset in datasets:
            self.response_handlers.update(dataset.get_handlers())

        self.response_handlers.update({
            'user_entity': handle_user_entity,
            'entity_listener': handle_entity_listener,
            'user_listening_activity': handle_user_listening_activity,
            'user_daily_activity': handle_user_daily_activity,
            'sitewide_entity': handle_sitewide_entity,
            'sitewide_listening_activity': handle_sitewide_listening_activity,
            'fresh_releases': handle_fresh_releases,
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
            'year_in_music_top_stats': handle_yim_top_stats,
            'year_in_music_listens_per_day': handle_yim_listens_per_day,
            'year_in_music_listen_count': handle_yim_listen_counts,
            'year_in_music_similar_users': handle_yim_similar_users,
            'year_in_music_new_releases_of_top_artists': handle_yim_new_releases_of_top_artists,
            'year_in_music_day_of_week': handle_yim_day_of_week,
            'year_in_music_most_listened_year': handle_yim_most_listened_year,
            'year_in_music_listening_time': handle_yim_listening_time,
            'year_in_music_artist_map': handle_yim_artist_map,
            'year_in_music_new_artists_discovered_count': handle_new_artists_discovered_count,
            'year_in_music_tracks_of_the_year_start': handle_yim_tracks_of_the_year_start,
            'year_in_music_tracks_of_the_year_data': handle_yim_tracks_of_the_year_data,
            'year_in_music_tracks_of_the_year_end': handle_yim_tracks_of_the_year_end,
            'troi_playlists': handle_troi_playlists,
            'troi_playlists_end': handle_troi_playlists_end,
        })

    def process_response(self, response):
        try:
            response_type = response['type']
        except (TypeError, KeyError):
            self.app.logger.error("Bad response sent to spark_reader: %s", json.dumps(response, indent=4),
                                  exc_info=True)
            return
        self.app.logger.info("Received message for %s", response_type)
        try:
            response_handler = self.response_handlers[response_type]
        except Exception:
            self.app.logger.error("Unknown response type: %s, doing nothing.", response_type, exc_info=True)
            return

        try:
            response_handler(response)
        except Exception as e:
            self.app.logger.error("Error in the spark reader response handler: data: %s",
                                  json.dumps(response, indent=4), exc_info=True)
            sentry_sdk.capture_exception(e)
            return

    def callback(self, message: Message):
        """ Handle the data received from the queue and
            insert into the database accordingly.
        """
        self.app.logger.debug("Received a message, processing...")
        response = orjson.loads(message.body)
        self.process_response(response)
        message.ack()
        self.app.logger.debug("Done!")

    def get_consumers(self, _, channel):
        return [Consumer(channel, queues=[self.spark_result_queue], on_message=lambda msg: self.callback(msg))]

    def init_rabbitmq_connection(self):
        self.connection = Connection(
            hostname=self.app.config["RABBITMQ_HOST"],
            userid=self.app.config["RABBITMQ_USERNAME"],
            port=self.app.config["RABBITMQ_PORT"],
            password=self.app.config["RABBITMQ_PASSWORD"],
            virtual_host=self.app.config["RABBITMQ_VHOST"],
            transport_options={"client_properties": {"connection_name": get_fallback_connection_name()}}
        )

    def start(self):
        """ initiates RabbitMQ connection and starts consuming from the queue
        """
        self.register_handlers()
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
                    self.app.logger.error("Error in SparkReader:", exc_info=True)
                    time.sleep(3)


if __name__ == '__main__':
    sr = SparkReader(create_app())
    sr.start()
