import json
import time

from kombu import Exchange, Queue, Connection, Consumer, Message
from kombu.mixins import ConsumerMixin

from listenbrainz.metadata_cache.crawler import Crawler
from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.utils import get_fallback_connection_name


class ServiceMetadataCache(ConsumerMixin):

    def __init__(self, app, handler: BaseHandler):
        self.app = app
        self.handler = handler
        self.crawler = None
        self.service = None

        self.connection = None
        self.service_channel = None
        self.unique_exchange = Exchange(self.app.config["UNIQUE_EXCHANGE"], "fanout", durable=False)
        # this queue gets album ids from listens
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
        self.service_queue = Queue(
            self.handler.get_external_service_queue_name(),
            exchange=self.external_services_exchange,
            durable=True
        )

    def get_consumers(self, _, channel):
        self.service_channel = channel.connection.channel()
        return [
            Consumer(channel, queues=[self.listens_queue], on_message=lambda x: self.process_listens(x)),
            Consumer(self.service_channel, queues=[self.service_queue], on_message=lambda x: self.process_seeder(x))
        ]

    def on_consume_end(self, connection, default_channel):
        if self.service_channel:
            self.service_channel.close()

    def process_listens(self, message: Message):
        listens = json.loads(message.body)
        for listen in listens:
            self.service.add_from_listen(listen)
        message.ack()

    def process_seeder(self, message: Message):
        body = json.loads(message.body)
        for album_id in body["album_ids"]:
            self.service.add_from_seeder(album_id)
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
                self.crawler = Crawler(self.app, self.handler)
                self.service.start()

                self.app.logger.info("Starting Spotify Metadata Cache ...")
                self.init_rabbitmq_connection()
                self.run()
            except KeyboardInterrupt:
                self.service.terminate()
                self.app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                self.app.logger.error("Error in Spotify Metadata Cache: ", exc_info=True)
                time.sleep(3)
        # the while True loop above makes this line unreachable but adding it anyway
        # so that we remember that every started thread should also be joined.
        # (you may also want to read the commit message for the commit that added this)
        self.service.terminate()
