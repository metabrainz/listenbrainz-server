import json
import time

from kombu import Exchange, Queue, Connection, Consumer, Message
from kombu.mixins import ConsumerMixin

from listenbrainz.spotify_metadata_cache.spotify_lookup_queue import SpotifyIdsQueue
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app


class SpotifyMetadataCache(ConsumerMixin):
    """ Main entry point for the mapping writer. Sets up connections and 
        handles messages from RabbitMQ and stuff them into the queue for the
        job matcher to handle."""

    def __init__(self, app):
        self.app = app
        self.queue = None
        self.connection = None
        self.unique_exchange = Exchange(self.app.config["UNIQUE_EXCHANGE"], "fanout", durable=False)
        # this queue gets spotify album ids from listens
        self.listens_queue = Queue(
            self.app.config["SPOTIFY_METADATA_QUEUE"],
            exchange=self.unique_exchange, 
            durable=True
        )
        self.external_services_exchange = Exchange(
            self.app.config["EXTERNAL_SERVICES_EXCHANGE"],
            "topic",
            durable=True
        )
        # this queue gets spotify album ids directly queued to the external spotify queue
        self.spotify_queue = Queue(
            self.app.config["EXTERNAL_SERVICES_SPOTIFY_CACHE_QUEUE"],
            exchange=self.external_services_exchange, 
            durable=True
        )

    def get_consumers(self, _, channel):
        self.spotify_channel = channel.connection.channel()
        return [
            Consumer(channel, queues=[self.listens_queue], on_message=lambda x: self.process_listens(x)),
            Consumer(self.spotify_channel, queues=[self.spotify_queue], on_message=lambda x: self.process_album_ids(x))
        ]

    def on_consume_end(self, connection, default_channel):
        if self.spotify_channel:
            self.spotify_channel.close()

    def process_listens(self, message: Message):
        listens = json.loads(message.body)

        for listen in listens:
            spotify_album_id = listen["track_metadata"]["additional_info"].get("spotify_album_id")
            if spotify_album_id:
                self.queue.add_spotify_ids(spotify_album_id)

        message.ack()

    def process_album_ids(self, message: Message):
        body = json.loads(message.body)
        for album_id in body["album_ids"]:
            self.queue.add_spotify_ids(album_id)
        message.ack()

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
        while True:
            try:
                self.app.logger.info("Starting queue stuffer...")
                self.queue = SpotifyIdsQueue(app)
                self.queue.start()

                self.app.logger.info("Starting Spotify Metadata Cache ...")
                self.init_rabbitmq_connection()
                self.run()
            except KeyboardInterrupt:
                self.queue.terminate()
                self.app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                self.app.logger.error("Error in Spotify Metadata Cache: ", exc_info=True)
                time.sleep(3)
        # the while True loop above makes this line unreachable but adding it anyway
        # so that we remember that every started thread should also be joined.
        # (you may also want to read the commit message for the commit that added this)
        self.queue.terminate()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        smc = SpotifyMetadataCache(app)
        smc.start()
