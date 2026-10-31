import json
import time
from collections import deque

from kombu.mixins import ConsumerMixin

from listenbrainz.listen import Listen, NowPlayingListen
from listenbrainz.rabbitmq import create_rabbitmq_connection

from kombu import Exchange, Queue, Consumer


# Maximum ordinary listen notifications per user per flush; must be a positive integer.
WEBSOCKETS_MAX_LISTENS_PER_FLUSH = 10
WEBSOCKETS_FLUSH_INTERVAL_SECONDS = 1


class ListensDispatcher(ConsumerMixin):

    def __init__(self, app, socketio):
        self.app = app
        self.socketio = socketio
        self.connection = None
        self.pending_listens = {}
        # there are two consumers, so we need two channels: one for playing now queue and another
        # for normal listens queue. when using ConsumerMixin, it sets up a default channel itself.
        # we create the other channel here. we also need to handle its cleanup later
        self.playing_now_channel = None

        self.unique_exchange = Exchange(app.config["UNIQUE_EXCHANGE"], "fanout", durable=True)
        self.playing_now_exchange = Exchange(app.config["PLAYING_NOW_EXCHANGE"], "fanout", durable=True)
        self.websockets_queue = Queue(app.config["WEBSOCKETS_QUEUE"], exchange=self.unique_exchange, durable=True)
        self.playing_now_queue = Queue(app.config["PLAYING_NOW_QUEUE"], exchange=self.playing_now_exchange,
                                       durable=True)

    def send_listens(self, event_name, message):
        listens = json.loads(message.body)
        for data in listens:
            if event_name == "playing_now":
                listen = NowPlayingListen(user_id=data["user_id"], user_name=data["user_name"], data=data["track_metadata"])
                self.socketio.emit(event_name, json.dumps(listen.to_api()), to=listen.user_name)
            else:
                user_name = data["user_name"]
                if user_name not in self.pending_listens:
                    self.pending_listens[user_name] = deque(maxlen=WEBSOCKETS_MAX_LISTENS_PER_FLUSH)
                self.pending_listens[user_name].append(data)
        # Listens are already stored upstream. Buffered notifications are best-effort.
        message.ack()

    def flush_listens(self):
        # Swap buffers before emitting can yield to the consumer. New arrivals
        # belong to the next flush, and inactive users are no longer retained.
        ready = self.pending_listens
        self.pending_listens = {}
        for user_name, listens in ready.items():
            for data in listens:
                try:
                    listen = Listen.from_json(data)
                    self.socketio.emit("listen", json.dumps(listen.to_api()), to=user_name)
                except Exception:
                    self.app.logger.error("Unable to emit listen notification for %s", user_name, exc_info=True)

    def flush_listens_periodically(self):
        while True:
            self.socketio.sleep(WEBSOCKETS_FLUSH_INTERVAL_SECONDS)
            try:
                self.flush_listens()
            except Exception:
                self.app.logger.error("Unable to flush listen notifications", exc_info=True)

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
        self.connection = create_rabbitmq_connection(self.app.config)

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
