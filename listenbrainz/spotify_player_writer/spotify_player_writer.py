import json
import listenbrainz.webserver
import pika
import time

from flask import current_app


class PlayerWriter:

    def __init__(self, app):
        self.app = app

    def callback_listen(self, channel, method, properties, body):
        x = json.loads(body)
        current_app.logger.error("from callback listen: %s", json.dumps(x, indent=4))
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def callback_playing_now(self, channel, method, properties, body):
        x = json.loads(body)
        current_app.logger.error("From callback playing now: %s", json.dumps(x, indent=4))
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def create_and_bind_exchange_and_queue(self, channel, exchange, queue):
        channel.exchange_declare(exchange=exchange, exchange_type='fanout')
        channel.queue_declare(callback=lambda x: None, queue=queue, durable=True)
        channel.queue_bind(callback=lambda x: None, exchange=exchange, queue=queue)

    def on_open_callback(self, channel):
        self.create_and_bind_exchange_and_queue(channel, current_app.config['UNIQUE_EXCHANGE'], current_app.config['FOLLOW_LIST_QUEUE'])
        channel.basic_consume(self.callback_listen, queue=current_app.config['FOLLOW_LIST_QUEUE'])

        self.create_and_bind_exchange_and_queue(channel, current_app.config['PLAYING_NOW_EXCHANGE'], current_app.config['PLAYING_NOW_QUEUE'])
        channel.basic_consume(self.callback_playing_now, queue=current_app.config['PLAYING_NOW_QUEUE'])

    def on_open(self, connection):
        connection.channel(self.on_open_callback)

    def init_rabbitmq_connection(self):
        while True:
            try:
                credentials = pika.PlainCredentials(current_app.config['RABBITMQ_USERNAME'], current_app.config['RABBITMQ_PASSWORD'])
                connection_parameters = pika.ConnectionParameters(
                    host=current_app.config['RABBITMQ_HOST'],
                    port=current_app.config['RABBITMQ_PORT'],
                    virtual_host=current_app.config['RABBITMQ_VHOST'],
                    credentials=credentials,
                )
                self.connection = pika.SelectConnection(parameters=connection_parameters, on_open_callback=self.on_open)
                break
            except Exception as e:
                current_app.logger.error("Error while connecting to RabbitMQ: %s", str(e), exc_info=True)
                time.sleep(3)


    def run(self):
        with self.app.app_context():
            while True:
                current_app.logger.info("Starting player writer...")
                current_app.logger.info("Connecting to RabbitMQ...")
                self.init_rabbitmq_connection()
                current_app.logger.info("Done!")
                current_app.logger.info("Started!")
                try:
                    self.connection.ioloop.start()
                except KeyboardInterrupt:
                    current_app.logger.error("Keyboard interrupt!")
                    break
                except Exception as e:
                    current_app.logger.error("Error in PlayerWriter: %s", str(e), exc_info=True)
                    time.sleep(3)

def main():
    PlayerWriter(listenbrainz.webserver.create_app()).run()

if __name__ == '__main__':
    main()
