import json
import time

from kombu.mixins import ConsumerMixin

from listenbrainz.listen import Listen, NowPlayingListen
from listenbrainz.utils import get_fallback_connection_name

from kombu import Connection, Exchange, Queue, Consumer


class ListensDispatcher(ConsumerMixin):

    def __init__(self, app, socketio):
        self.app = app
        self.socketio = socketio
        self.connection = None
        # there are two consumers, so we need two channels: one for playing now queue and another
        # for normal listens queue. when using ConsumerMixin, it sets up a default channel itself.
        # we create the other channel here. we also need to handle its cleanup later
        self.playing_now_channel = None

        self.unique_exchange = Exchange(app.config["UNIQUE_EXCHANGE"], "fanout", durable=False)
        self.playing_now_exchange = Exchange(app.config["PLAYING_NOW_EXCHANGE"], "fanout", durable=False)
        self.websockets_queue = Queue(app.config["WEBSOCKETS_QUEUE"], exchange=self.unique_exchange, durable=True)
        self.playing_now_queue = Queue(app.config["PLAYING_NOW_QUEUE"], exchange=self.playing_now_exchange,
                                       durable=True)

    def send_listens(self, event_name, message):
        listens = json.loads(message.body)
        for data in listens:
            if event_name == "playing_now":
                listen = NowPlayingListen(user_id=data["user_id"], user_name=data["user_name"], data=data["track_metadata"])
            else:
                listen = Listen.from_json(data)
            self.socketio.emit(event_name, json.dumps(listen.to_api()), to=listen.user_name)
        message.ack()

    def get_consumers(self, _, channel):
        self.playing_now_channel = channel.connection.channel()
        return [
            Consumer(channel, queues=[self.websockets_queue],
                     on_message=lambda x: self.send_listens("listen", x)),
            Consumer(self.playing_now_channel, queues=[self.playing_now_queue],
                     on_message=lambda x: self.send_listens("playing_now", x))
        ]

    def on_consume_end(self, connection, default_channel):
        if self.playing_now_channel:
            self.playing_now_channel.close()

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
                self.app.logger.info("Starting player writer...")
                self.init_rabbitmq_connection()
                self.run()
            except KeyboardInterrupt:
                self.app.logger.error("Keyboard interrupt!")
                break
            except Exception:
                self.app.logger.error("Error in PlayerWriter:", exc_info=True)
                time.sleep(3)
