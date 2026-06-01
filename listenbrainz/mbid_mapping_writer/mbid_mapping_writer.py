import json
import time

from kombu import Exchange, Queue, Consumer, Message
from kombu.mixins import ConsumerMixin

from listenbrainz.rabbitmq import create_rabbitmq_connection
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
        self.connection = create_rabbitmq_connection(self.app.config)

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
    # Pool sizing for the writer process:
    #   ts: 3 ThreadPoolExecutor workers (matcher) each hold up to 2 timescale
    #       connections at peak (ts_conn for the surrounding work + a brief
    #       raw_connection() inside recording_lookup_base) → 6, plus 1 main
    #       job_queue thread + 1 occasional legacy loader ≈ 8 concurrent users.
    #   db / meb: writer never touches them, keep the pool minimal so we don't
    #       hold idle slots on pgbouncer-master for nothing.
    app = create_app(
        use_pool=True,
        pool_size_overrides={
            "db": (1, 1),
            "ts": (6, 4),
            "meb": (1, 1),
        },
    )
    with app.app_context():
        mw = MBIDMappingWriter(app)
        mw.start()
