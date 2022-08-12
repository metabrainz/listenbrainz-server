#!/usr/bin/env python3
import time
from datetime import datetime
from time import monotonic

import psycopg2
import ujson
from brainzutils import metrics
from flask import current_app
from kombu import Exchange, Queue, Consumer, Message, Connection
from kombu.entity import PERSISTENT_DELIVERY_MODE
from kombu.utils.debug import setup_logging
from kombu.mixins import ConsumerProducerMixin
from more_itertools import chunked

from listenbrainz import messybrainz
from listenbrainz.listen import Listen
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app, redis_connection, timescale_connection
from listenbrainz.webserver.views.api_tools import MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP

import eventlet
eventlet.monkey_patch()

METRIC_UPDATE_INTERVAL = 60  # seconds
LISTEN_INSERT_ERROR_SENTINEL = -1  #


class TimescaleWriterSubscriber(ConsumerProducerMixin):

    def __init__(self):
        self.connection = None

        self.incoming_exchange = Exchange(current_app.config["INCOMING_EXCHANGE"], "fanout", durable=False)
        self.incoming_queue = Queue(current_app.config["INCOMING_QUEUE"], exchange=self.incoming_exchange, durable=True)
        self.unique_exchange = Exchange(current_app.config["UNIQUE_EXCHANGE"], "fanout", durable=False)
        self.unique_queue = Queue(current_app.config["UNIQUE_QUEUE"], exchange=self.unique_exchange, durable=True)

        self.ERROR_RETRY_DELAY = 3  # number of seconds to wait until retrying an operation

        # these are counts since the last metric update was submitted
        self.incoming_listens = 0
        self.unique_listens = 0
        self.metric_submission_time = monotonic() + METRIC_UPDATE_INTERVAL

    def get_consumers(self, _, channel):
        return [Consumer(channel, queues=[self.incoming_queue], on_message=self.callback)]

    def callback(self, body, message: Message):

        listens = ujson.loads(body)

        msb_listens = []
        for chunk in chunked(listens, MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP):
            msb_listens.extend(self.messybrainz_lookup(chunk))

        submit = []
        for listen in msb_listens:
            try:
                submit.append(Listen.from_json(listen))
            except ValueError:
                pass

        ret = self.insert_to_listenstore(submit)

        # If there is an error, we do not ack the message so that rabbitmq redelivers it later.
        if ret == LISTEN_INSERT_ERROR_SENTINEL:
            return ret

        message.ack()

        return ret

    def messybrainz_lookup(self, listens):
        msb_listens = []
        for listen in listens:
            messy_dict = {
                'artist': listen['track_metadata']['artist_name'],
                'title': listen['track_metadata']['track_name'],
            }
            if 'release_name' in listen['track_metadata']:
                messy_dict['release'] = listen['track_metadata']['release_name']

            if 'additional_info' in listen['track_metadata']:
                ai = listen['track_metadata']['additional_info']
                if 'artist_mbids' in ai and isinstance(ai['artist_mbids'], list):
                    messy_dict['artist_mbids'] = sorted(ai['artist_mbids'])
                if 'release_mbid' in ai:
                    messy_dict['release_mbid'] = ai['release_mbid']
                if 'recording_mbid' in ai:
                    messy_dict['recording_mbid'] = ai['recording_mbid']
                if 'track_number' in ai:
                    messy_dict['track_number'] = ai['track_number']
                if 'spotify_id' in ai:
                    messy_dict['spotify_id'] = ai['spotify_id']

            msb_listens.append(messy_dict)

        try:
            msb_responses = messybrainz.submit_listens_and_sing_me_a_sweet_song(msb_listens)
        except (messybrainz.exceptions.BadDataException, messybrainz.exceptions.ErrorAddingException):
            current_app.logger.error("MessyBrainz lookup for listens failed: ", exc_info=True)
            return []

        augmented_listens = []
        for listen, messybrainz_resp in zip(listens, msb_responses['payload']):
            messybrainz_resp = messybrainz_resp['ids']

            if 'additional_info' not in listen['track_metadata']:
                listen['track_metadata']['additional_info'] = {}

            try:
                listen['recording_msid'] = messybrainz_resp['recording_msid']
                listen['track_metadata']['additional_info']['artist_msid'] = messybrainz_resp['artist_msid']
            except KeyError:
                current_app.logger.error("MessyBrainz did not return a proper set of ids")
                return []

            try:
                listen['track_metadata']['additional_info']['release_msid'] = messybrainz_resp['release_msid']
            except KeyError:
                pass

            augmented_listens.append(listen)
        return augmented_listens

    def insert_to_listenstore(self, data):
        """
        Inserts a batch of listens to the ListenStore. Timescale will report back as
        to which rows were actually inserted into the DB, allowing us to send those
        down the unique queue.

        Args:
            data: the data to be inserted into the ListenStore

        Returns: number of listens successfully sent or LISTEN_INSERT_ERROR_SENTINEL
        if there was an error in inserting listens
        """

        if not data:
            return 0

        self.incoming_listens += len(data)
        try:
            rows_inserted = timescale_connection._ts.insert(data)
        except psycopg2.OperationalError as err:
            current_app.logger.error("Cannot write data to listenstore: %s. Sleep." % str(err), exc_info=True)
            time.sleep(self.ERROR_RETRY_DELAY)
            return LISTEN_INSERT_ERROR_SENTINEL

        if not rows_inserted:
            return len(data)

        try:
            redis_connection._redis.increment_listen_count_for_day(day=datetime.utcnow(), count=len(rows_inserted))
        except Exception:
            # Not critical, so if this errors out, just log it to Sentry and move forward
            current_app.logger.error("Could not update listen count per day in redis", exc_info=True)

        unique = []
        inserted_index = {}
        for inserted in rows_inserted:
            inserted_index['%d-%s-%s' % (inserted[0], inserted[1], inserted[2])] = 1

        for listen in data:
            k = '%d-%s-%s' % (listen.ts_since_epoch, listen.data['track_name'], listen.user_name)
            if k in inserted_index:
                unique.append(listen)

        if not unique:
            return len(data)

        redis_connection._redis.update_recent_listens(unique)
        self.unique_listens += len(unique)

        self.producer.publish(
            exchange=self.unique_exchange,
            routing_key="",
            body=ujson.dumps([listen.to_json() for listen in unique]),
            delivery_mode=PERSISTENT_DELIVERY_MODE,
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
        current_app.logger.info("timescale-writer init")
        self.init_rabbitmq_connection()
        self.run()


if __name__ == "__main__":
    setup_logging()
    app = create_app()
    with app.app_context():
        rc = TimescaleWriterSubscriber()
        rc.start()
