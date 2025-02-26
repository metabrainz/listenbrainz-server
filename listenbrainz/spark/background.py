import json
import logging
from queue import Queue, Empty
from threading import Thread

import orjson
import sentry_sdk

from listenbrainz.spark.handlers import (
    handle_candidate_sets,
    handle_dataframes,
    handle_dump_imported,
    handle_model,
    handle_recommendations,
    handle_sitewide_entity,
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
    handle_yim_listening_time,
    handle_yim_new_artists_discovered_count,
    handle_yim_artist_map,
    handle_troi_playlists,
    handle_troi_playlists_end,
    handle_yim_top_genres,
    handle_yim_playlists,
    handle_yim_playlists_end,
    handle_echo,
    handle_sitewide_artist_map
)
from listenbrainz.spark.spark_dataset import CouchDbDataset, UserEntityStatsDataset, DailyActivityStatsDataset, \
    ListeningActivityStatsDataset, EntityListenerStatsDataset
from listenbrainz.db.popularity import get_all_popularity_datasets
from listenbrainz.db.similarity import SimilarRecordingsDataset, SimilarArtistsDataset
from listenbrainz.db.tags import TagsDataset
from listenbrainz.webserver import ts_conn, db_conn


logger = logging.getLogger(__name__)


class BackgroundJobProcessor:
    """ To handle long-running tasks without skipping heartbeats in the main thread, a background message processor
    that runs in a separate thread.

    This setup is useful when processing a message (even rarely) can take over a minute. Processing such tasks
    in the main thread can cause missed heartbeats which in turn lead to the connection being restarted and the same
    messages being redelivered to the consumer setting up a loop. The rabbitmq queue essentially gets stuck and the
    consumer keeps processing the same messages again and again.

    This processor runs in its own thread. However, that presents another challenge because messages need to be ack-ed
    from the same thread on which they were received (the restriction is about channels ack-ing from the same
    channel but channels are not thread-safe, hence same thread). Here's a brief explanation of how the overall flow
    works:

        1. The RabbitMQ consumer listens for messages on the main thread.
        2. Upon receiving a message, the RabbitMQ callback enqueues the message into the processor's message queue.
        3. The processor handles the message and, upon completion, enqueues the message into its acknowledgment queue.
        4. The main thread periodically checks the processor's acknowledgment queue for completed messages and acknowledges them.
    """

    def __init__(self, app):
        self.app = app
        self.thread = None
        self.done = False
        self.internal_message_queue = Queue()
        self.internal_message_ack_queue = Queue()

        self.datasets = [
            CouchDbDataset,
            UserEntityStatsDataset,
            DailyActivityStatsDataset,
            ListeningActivityStatsDataset,
            EntityListenerStatsDataset,
            SimilarRecordingsDataset,
            SimilarArtistsDataset,
            TagsDataset,
            *get_all_popularity_datasets()
        ]
        self.response_handlers = {}
        self.register_handlers()

    def terminate(self):
        """ Stop the background job processor and its thread """
        self.done = True
        self.thread.join()

    def enqueue(self, message):
        """ Add a message for processing to internal queue """
        self.internal_message_queue.put(message, block=False)

    def pending_acks(self):
        """ Add a processed message to internal queue for acknowledging the message to rabbitmq. """
        messages = []
        while True:
            try:
                message = self.internal_message_ack_queue.get(block=False)
                messages.append(message)
            except Empty:
                break
        return messages

    def run(self):
        """ Infinite loop that keeps processing messages enqueued in the internal message queue and puts them on
         ack queue if successfully processed.
        """
        with self.app.app_context():
            while not self.done:
                try:
                    message = self.internal_message_queue.get(block=True, timeout=5)
                    self.process_message(message)
                    self.internal_message_ack_queue.put(message)
                except Empty:
                    self.app.logger.debug("Empty internal message queue")

            self.stop()


    def stop(self):
        """ Stop running spark reader and associated handlers """
        for dataset in self.datasets:
            dataset.handle_shutdown()

    def start(self):
        """ Start running the background job processor in its own thread """
        self.thread = Thread(target=self.run, name="SparkReaderBackgroundJobProcessor")
        self.thread.start()

    def register_handlers(self):
        """ Register handlers for the Spark reader """
        for dataset in self.datasets:
            self.response_handlers.update(dataset.get_handlers())

        self.response_handlers.update({
            "echo": handle_echo,
            "sitewide_entity": handle_sitewide_entity,
            "sitewide_listening_activity": handle_sitewide_listening_activity,
            "sitewide_artist_map": handle_sitewide_artist_map,
            "fresh_releases": handle_fresh_releases,
            "import_full_dump": handle_dump_imported,
            "import_incremental_dump": handle_dump_imported,
            "cf_recommendations_recording_dataframes": handle_dataframes,
            "cf_recommendations_recording_model": handle_model,
            "cf_recommendations_recording_candidate_sets": handle_candidate_sets,
            "cf_recommendations_recording_recommendations": handle_recommendations,
            "import_mapping": notify_mapping_import,
            "missing_musicbrainz_data": handle_missing_musicbrainz_data,
            "cf_recommendations_recording_mail": cf_recording_recommendations_complete,
            "similar_users": handle_similar_users,
            "year_in_music_top_stats": handle_yim_top_stats,
            "year_in_music_listens_per_day": handle_yim_listens_per_day,
            "year_in_music_listen_count": handle_yim_listen_counts,
            "year_in_music_similar_users": handle_yim_similar_users,
            "year_in_music_new_releases_of_top_artists": handle_yim_new_releases_of_top_artists,
            "year_in_music_day_of_week": handle_yim_day_of_week,
            "year_in_music_most_listened_year": handle_yim_most_listened_year,
            "year_in_music_listening_time": handle_yim_listening_time,
            "year_in_music_artist_map": handle_yim_artist_map,
            "year_in_music_new_artists_discovered_count": handle_yim_new_artists_discovered_count,
            "year_in_music_top_genres": handle_yim_top_genres,
            "year_in_music_playlists": handle_yim_playlists,
            "year_in_music_playlists_end": handle_yim_playlists_end,
            "troi_playlists": handle_troi_playlists,
            "troi_playlists_end": handle_troi_playlists_end,
        })

    def process_message(self, message):
        """ Process a message received by the spark reader """
        try:
            response = orjson.loads(message.body)
        except Exception:
            self.app.logger.error("Error processing message: %s", message)
            return

        try:
            response_type = response["type"]
            self.app.logger.info("Received message for %s", response_type)
        except (TypeError, KeyError):
            self.app.logger.error("Bad response sent to spark_reader: %s", json.dumps(response, indent=4),
                                  exc_info=True)
            return

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
        finally:
            db_conn.rollback()
            ts_conn.rollback()
