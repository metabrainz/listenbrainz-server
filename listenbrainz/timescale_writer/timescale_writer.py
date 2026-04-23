#!/usr/bin/env python3
import time
from datetime import datetime
from time import monotonic

import psycopg2
import orjson
import sentry_sdk
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
    PREFETCH_COUNT = 500

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
                prefetch_count=self.PREFETCH_COUNT
            )
        ]

    @staticmethod
    def _summarize_raw_listens(listens):
        user_ids = sorted({listen.get("user_id") for listen in listens if listen.get("user_id") is not None})
        timestamps = [listen.get("listened_at") for listen in listens if listen.get("listened_at") is not None]
        return {
            "listen_count": len(listens),
            "user_count": len(user_ids),
            "sample_user_ids": user_ids[:5],
            "min_listened_at": min(timestamps) if timestamps else None,
            "max_listened_at": max(timestamps) if timestamps else None,
        }

    @staticmethod
    def _summarize_listen_objects(listens):
        user_ids = sorted({listen.user_id for listen in listens if listen.user_id is not None})
        timestamps = [listen.ts_since_epoch for listen in listens if listen.ts_since_epoch is not None]
        return {
            "listen_count": len(listens),
            "user_count": len(user_ids),
            "sample_user_ids": user_ids[:5],
            "min_listened_at": min(timestamps) if timestamps else None,
            "max_listened_at": max(timestamps) if timestamps else None,
        }

    def callback(self, message: Message):
        """ Process a message from the incoming queue.

            1. If a listen inserts successfully, send it to the unique queue. Ack the incoming message.
            2. If a listen fails to insert, send it to the rejection queue. Ack the incoming message. If
               adding the message to the rejection queue fails, bubble up the error to cause a service
               restart.
            3. If a listen fails to insert due to a database error, sleep for a few seconds and bubble up
               the error to cause a service restart.
        """
        with sentry_sdk.start_transaction(op="queue.process", name="timescale_writer.process_listens") as transaction:
            transaction.set_data("incoming_queue", self.incoming_queue.name)
            transaction.set_data("message_bytes", len(message.body) if message.body is not None else 0)
            try:
                with sentry_sdk.start_span(op="deserialize", name="decode incoming listen batch") as span:
                    listens = orjson.loads(message.body)
                    raw_summary = self._summarize_raw_listens(listens)
                    span.set_data("listen_count", raw_summary["listen_count"])
                    span.set_data("user_count", raw_summary["user_count"])

                transaction.set_data("listen_count", raw_summary["listen_count"])
                transaction.set_data("user_count", raw_summary["user_count"])
                transaction.set_data(
                    "messybrainz_chunk_count",
                    (len(listens) + MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP - 1) // MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP,
                )

                msb_listens = []
                for chunk_number, chunk in enumerate(chunked(listens, MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP), start=1):
                    msb_listens.extend(self.messybrainz_lookup(chunk, chunk_number=chunk_number))

                with sentry_sdk.start_span(op="listen.prepare", name="build Listen objects from queue payload") as span:
                    span.set_data("listen_count", len(msb_listens))
                    submit = [Listen.from_json(listen) for listen in msb_listens]
                    submit_summary = self._summarize_listen_objects(submit)
                    span.set_data("user_count", submit_summary["user_count"])

                with sentry_sdk.start_span(op="listenstore", name="insert listen batch into ListenStore") as span:
                    span.set_data("listen_count", len(submit))
                    processed = self.insert_to_listenstore(submit)
                    span.set_data("processed_count", processed)
            except psycopg2.OperationalError:
                current_app.logger.error("Error processing listens due to database issues:", exc_info=True)
                time.sleep(self.ERROR_RETRY_DELAY)
                raise
            except Exception:
                current_app.logger.error("Error processing listens, publishing to rejection queue:", exc_info=True)
                try:
                    with sentry_sdk.start_span(op="queue.publish", name="publish rejected listen batch") as span:
                        span.set_data("message_bytes", len(message.body) if message.body is not None else 0)
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

            with sentry_sdk.start_span(op="queue.ack", name="ack incoming listen batch") as span:
                span.set_data("delivery_tag", getattr(message, "delivery_tag", None))
                message.ack()

    def messybrainz_lookup(self, listens, chunk_number=None):
        with sentry_sdk.start_span(op="messybrainz", name="lookup recording msids for listen chunk") as span:
            span.set_data("listen_count", len(listens))
            if chunk_number is not None:
                span.set_data("chunk_number", chunk_number)
            with sentry_sdk.start_span(op="listen.prepare", name="build MessyBrainz lookup payload") as build_span:
                build_span.set_data("listen_count", len(listens))
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

            with sentry_sdk.start_span(op="db", name="submit listen chunk to MessyBrainz") as lookup_span:
                lookup_span.set_data("listen_count", len(msb_listens))
                msb_responses = messybrainz.submit_listens_and_sing_me_a_sweet_song(msb_listens)
                lookup_span.set_data("response_count", len(msb_responses))
            if len(msb_responses) != len(listens):
                current_app.logger.warning(
                    "Timescale Writer got unexpected MessyBrainz response size=%d expected=%d",
                    len(msb_responses),
                    len(listens),
                )

            with sentry_sdk.start_span(op="listen.prepare", name="attach recording msids to listens") as attach_span:
                attach_span.set_data("listen_count", len(listens))
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

        with sentry_sdk.start_span(op="db", name="insert listens into Timescale") as span:
            span.set_data("listen_count", len(data))
            rows_inserted = timescale_connection._ts.insert(data)
            span.set_data("rows_inserted", len(rows_inserted) if rows_inserted is not None else None)
        if rows_inserted is None:
            current_app.logger.warning(
                "Timescale Writer insert returned None for batch size=%d; batch was not published to unique queue",
                len(data),
            )
            return len(data)
        if not rows_inserted:
            return len(data)

        try:
            with sentry_sdk.start_span(op="cache", name="update daily listen count cache") as span:
                span.set_data("rows_inserted", len(rows_inserted))
                redis_connection._redis.increment_listen_count_for_day(day=datetime.today(), count=len(rows_inserted))
        except Exception:
            # Not critical, so if this errors out, just log it to Sentry and move forward
            current_app.logger.error("Could not update listen count per day in redis", exc_info=True)

        with sentry_sdk.start_span(op="listen.prepare", name="match inserted rows to unique listens") as span:
            span.set_data("listen_count", len(data))
            span.set_data("rows_inserted", len(rows_inserted))
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
            span.set_data("unique_count", len(unique))
            span.set_data("cache_invalidation_count", len(user_ids_to_invalidate))

        if not unique:
            return len(data)

        if user_ids_to_invalidate:
            try:
                with sentry_sdk.start_span(op="cache", name="invalidate user listen caches") as span:
                    span.set_data("user_count", len(user_ids_to_invalidate))
                    for user_id in user_ids_to_invalidate:
                        invalidate_user_listen_caches(user_id)
            except Exception:
                current_app.logger.error("Unable to invalidate listen cache:", exc_info=True)

        with sentry_sdk.start_span(op="cache", name="update recent listens cache") as span:
            span.set_data("listen_count", len(unique))
            redis_connection._redis.update_recent_listens(unique)
        self.unique_listens += len(unique)

        with sentry_sdk.start_span(op="queue.publish", name="publish unique listens") as span:
            span.set_data("listen_count", len(unique))
            span.set_data("exchange", self.unique_exchange.name)
            self.producer.publish(
                exchange=self.unique_exchange,
                routing_key="",
                body=orjson.dumps([listen.to_json() for listen in unique]).decode("utf-8"),
                delivery_mode=PERSISTENT_DELIVERY_MODE
            )

        if monotonic() > self.metric_submission_time:
            with sentry_sdk.start_span(op="metrics", name="update timescale writer metrics") as span:
                span.set_data("incoming_listens", self.incoming_listens)
                span.set_data("unique_listens", self.unique_listens)
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
