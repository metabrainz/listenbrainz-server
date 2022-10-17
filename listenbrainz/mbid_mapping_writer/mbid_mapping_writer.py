import json
import time

from kombu import Exchange, Queue, Connection, Consumer, Message
from kombu.mixins import ConsumerMixin

from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app
from listenbrainz.mbid_mapping_writer.job_queue import MappingJobQueue


class MBIDMappingWriter(ConsumerMixin):
    """ Main entry point for the mapping writer. Sets up connections and 
        handles messages from RabbitMQ and stuff them into the queue for the
        job matcher to handle."""

    def __init__(self, app):
        self.app = app
        self.queue = None
        self.connection = None
        self.unique_exchange = Exchange(self.app.config["UNIQUE_EXCHANGE"], "fanout", durable=False)
        self.unique_queue = Queue(self.app.config["UNIQUE_QUEUE"], exchange=self.unique_exchange, durable=True)

    def get_consumers(self, _, channel):
        return [Consumer(channel, queues=[self.unique_queue], on_message=lambda x: self.callback(x))]

    def callback(self, message: Message):
        listens = json.loads(message.body)
        self.queue.add_new_listens(listens)
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
                self.queue = MappingJobQueue(app)
                self.queue.start()

                self.app.logger.info("Starting MBID mapping writer...")
                self.init_rabbitmq_connection()
                self.run()
            except KeyboardInterrupt:
                self.queue.terminate()
                self.app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                self.app.logger.error("Error in MBID Mapping Writer: ", exc_info=True)
                time.sleep(3)
        # the while True loop above makes this line unreachable but adding it anyway
        # so that we remember that every started thread should also be joined.
        # (you may also want to read the commit message for the commit that added this)
        self.queue.terminate()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        mw = MBIDMappingWriter(app)
        mw.start()
