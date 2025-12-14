#!/usr/bin/env python3
import time
from datetime import datetime
from time import monotonic

import psycopg2
import orjson
from brainzutils import metrics
from flask import current_app
from kombu import Exchange, Queue, Consumer, Message, Connection
from kombu.entity import PERSISTENT_DELIVERY_MODE
from kombu.mixins import ConsumerProducerMixin
from more_itertools import chunked

from listenbrainz import messybrainz
from listenbrainz.listen import Listen
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app, redis_connection, timescale_connection
from listenbrainz.webserver.listens_cache import invalidate_user_listen_caches
from listenbrainz.webserver.views.api_tools import MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP

METRIC_UPDATE_INTERVAL = 60  # seconds


class TimescaleWriterSubscriber(ConsumerProducerMixin):

    def __init__(self):
        self.connection = None

        self.incoming_exchange = Exchange(current_app.config["INCOMING_EXCHANGE"], "fanout", durable=False)
        self.incoming_queue = Queue(current_app.config["INCOMING_QUEUE"], exchange=self.incoming_exchange, durable=True)
        self.unique_exchange = Exchange(current_app.config["UNIQUE_EXCHANGE"], "fanout", durable=False)
        self.unique_queue = Queue(current_app.config["UNIQUE_QUEUE"], exchange=self.unique_exchange, durable=True)
        self.rejection_exchange = Exchange(current_app.config["REJECTION_EXCHANGE"], "fanout", durable=True)
        self.rejection_queue = Queue(current_app.config["REJECTION_QUEUE"], exchange=self.rejection_exchange, durable=True)

        self.ERROR_RETRY_DELAY = 3  # number of seconds to wait until retrying an operation

        # these are counts since the last metric update was submitted
        self.incoming_listens = 0
        self.unique_listens = 0
        self.metric_submission_time = monotonic() + METRIC_UPDATE_INTERVAL

    def get_consumers(self, _, channel):
        return [
            Consumer(
                channel,
                queues=[self.incoming_queue],
                on_message=lambda x: self.callback(x),
                prefetch_count=500
            )
        ]

    def callback(self, message: Message):
        """ Process a message from the incoming queue.

            1. If a listen inserts successfully, send it to the unique queue. Ack the incoming message.
            2. If a listen fails to insert, send it to the rejection queue. Ack the incoming message. If
               adding the message to the rejection queue fails, bubble up the error to cause a service
               restart.
            3. If a listen fails to insert due to a database error, sleep for a few seconds and bubble up
               the error to cause a service restart.
        """
        try:
            listens = orjson.loads(message.body)

            msb_listens = []
            for chunk in chunked(listens, MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP):
                msb_listens.extend(self.messybrainz_lookup(chunk))

            submit = [Listen.from_json(listen) for listen in msb_listens]
            self.insert_to_listenstore(submit)
        except psycopg2.OperationalError:
            current_app.logger.error("Error processing listens due to database issues:", exc_info=True)
            time.sleep(self.ERROR_RETRY_DELAY)
            raise
        except Exception:
            current_app.logger.error("Error processing listens, publishing to rejection queue:", exc_info=True)
            try:
                self.producer.publish(
                    exchange=self.rejection_exchange,
                    routing_key="",
                    body=message.body,
                    delivery_mode=PERSISTENT_DELIVERY_MODE,
                    declare=[self.rejection_exchange, self.rejection_queue]
                )
            except Exception:
                current_app.logger.error("Failed to publish to rejection queue:", exc_info=True)
                time.sleep(self.ERROR_RETRY_DELAY)
                raise

        message.ack()

    def messybrainz_lookup(self, listens):
        msb_listens = []
        for listen in listens:
            if 'additional_info' not in listen['track_metadata']:
                listen['track_metadata']['additional_info'] = {}

            data = {
                'artist': listen['track_metadata']['artist_name'],
                'title': listen['track_metadata']['track_name'],
                'release': listen['track_metadata'].get('release_name'),
            }
            track_number = listen['track_metadata']['additional_info'].get('track_number')
            if track_number:
                data['track_number'] = str(track_number)

            duration = listen['track_metadata']['additional_info'].get('duration')
            if duration:
                data['duration'] = duration * 1000  # convert into ms
            else:  # try duration_ms field next
                duration_ms = listen['track_metadata']['additional_info'].get('duration_ms')
                if duration:
                    data['duration'] = duration_ms

            msb_listens.append(data)

        msb_responses = messybrainz.submit_listens_and_sing_me_a_sweet_song(msb_listens)

        augmented_listens = []
        for listen, msid in zip(listens, msb_responses):
            listen['recording_msid'] = msid
            augmented_listens.append(listen)
        return augmented_listens

    def insert_to_listenstore(self, data):
        """
        Inserts a batch of listens to the ListenStore. Timescale will report back as
        to which rows were actually inserted into the DB, allowing us to send those
        down the unique queue.

        Args:
            data: the data to be inserted into the ListenStore

        Returns: number of listens successfully sent

        Raises: psycopg2.OperationalError if there was an error in inserting listens
        """
        if not data:
            return 0

        self.incoming_listens += len(data)

        rows_inserted = timescale_connection._ts.insert(data)
        if not rows_inserted:
            return len(data)

        try:
            redis_connection._redis.increment_listen_count_for_day(day=datetime.today(), count=len(rows_inserted))
        except Exception:
            # Not critical, so if this errors out, just log it to Sentry and move forward
            current_app.logger.error("Could not update listen count per day in redis", exc_info=True)

        unique = []
        inserted_index = {}
        user_ids_to_invalidate = set()
        for inserted in rows_inserted:
            inserted_index['%d-%s-%s' % (int(inserted[0].timestamp()), inserted[1], inserted[2])] = 1
            user_ids_to_invalidate.add(inserted[1])

        for listen in data:
            k = '%d-%s-%s' % (listen.ts_since_epoch, listen.user_id, listen.recording_msid)
            if k in inserted_index:
                unique.append(listen)

        if not unique:
            return len(data)

        if user_ids_to_invalidate:
            try:
                for user_id in user_ids_to_invalidate:
                    invalidate_user_listen_caches(user_id)
            except Exception:
                current_app.logger.error("Unable to invalidate listen cache:", exc_info=True)

        redis_connection._redis.update_recent_listens(unique)
        self.unique_listens += len(unique)

        self.producer.publish(
            exchange=self.unique_exchange,
            routing_key="",
            body=orjson.dumps([listen.to_json() for listen in unique]).decode("utf-8"),
            delivery_mode=PERSISTENT_DELIVERY_MODE
        )

        if monotonic() > self.metric_submission_time:
            self.metric_submission_time += METRIC_UPDATE_INTERVAL
            metrics.set("timescale_writer", incoming_listens=self.incoming_listens, unique_listens=self.unique_listens)
            self.incoming_listens = 0
            self.unique_listens = 0

        return len(data)

    def init_rabbitmq_connection(self):
        self.connection = Connection(
            hostname=current_app.config["RABBITMQ_HOST"],
            userid=current_app.config["RABBITMQ_USERNAME"],
            port=current_app.config["RABBITMQ_PORT"],
            password=current_app.config["RABBITMQ_PASSWORD"],
            virtual_host=current_app.config["RABBITMQ_VHOST"],
            transport_options={"client_properties": {"connection_name": get_fallback_connection_name()}}
        )

    def start(self):
        while True:
            try:
                current_app.logger.info("Timescale Writer started.")
                self.init_rabbitmq_connection()
                self.run()
            except KeyboardInterrupt:
                current_app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                current_app.logger.error("Error in Timescale Writer:", exc_info=True)
                current_app.logger.error("Sleeping 3 seconds and exiting...", exc_info=True)
                time.sleep(self.ERROR_RETRY_DELAY)
                break


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        rc = TimescaleWriterSubscriber()
        rc.start()
