import json
import time

from kombu.mixins import ConsumerMixin

from listenbrainz.utils import get_fallback_connection_name

from kombu import Connection, Exchange, Queue, Consumer
from flask import current_app


class ListensDispatcher(ConsumerMixin):

    def __init__(self, app, socketio):
        self.app = app
        self.socketio = socketio
        self.connection = None
        self.channel2 = None

        self.unique_exchange = Exchange(app.config["UNIQUE_EXCHANGE"], "fanout")
        self.playing_now_exchange = Exchange(app.config["PLAYING_NOW_EXCHANGE"], "fanout")
        self.websockets_queue = Queue(app.config["WEBSOCKETS_QUEUE"], exchange=self.unique_exchange, durable=True)
        self.playing_now_queue = Queue(app.config["PLAYING_NOW_QUEUE"], exchange=self.playing_now_exchange, durable=True)

    def send_listens(self, event_name, body, message):
        listens = json.loads(body)
        for listen in listens:
            self.socketio.emit(event_name, json.dumps(listen), to=listen["user_name"])
        message.ack()

    def get_consumers(self, _, channel):
        self.channel2 = self.connection.channel()
        return [
            Consumer(channel, queues=[self.websockets_queue],
                     callbacks=[lambda body, message: self.send_listens("listen", body, message)]),
            Consumer(self.channel2, queues=[self.playing_now_queue],
                     callbacks=[lambda body, message: self.send_listens("playing_now", body, message)])
        ]

    def on_consume_end(self, connection, default_channel):
        if self.channel2:
            self.channel2.close()

    def init_rabbitmq_connection(self):
        while True:
            try:
                self.connection = Connection(
                    hostname=current_app.config["RABBITMQ_HOST"],
                    userid=current_app.config["RABBITMQ_USERNAME"],
                    port=current_app.config["RABBITMQ_PORT"],
                    password=current_app.config["RABBITMQ_PASSWORD"],
                    virtual_host=current_app.config["RABBITMQ_VHOST"],
                    client_properties={"connection_name": get_fallback_connection_name()}
                )
                break
            except Exception as e:
                current_app.logger.error("Error while connecting to RabbitMQ: %s", str(e), exc_info=True)
                time.sleep(3)

    def start(self):
        with self.app.app_context():
            while True:
                current_app.logger.info("Starting player writer...")
                self.init_rabbitmq_connection()
                try:
                    self.run()
                except KeyboardInterrupt:
                    current_app.logger.error("Keyboard interrupt!")
                    break
                except Exception as e:
                    current_app.logger.error("Error in PlayerWriter: %s", str(e), exc_info=True)
                    time.sleep(3)
