import click
import listenbrainz.utils as utils
import pika
import ujson

from listenbrainz import db
from listenbrainz import stats
from listenbrainz.webserver import create_app

from flask import current_app

cli = click.Group()

def send_message_to_spark_cluster(message):
    with create_app().app_context():
        rabbitmq_connection = utils.connect_to_rabbitmq(
            username=current_app.config['RABBITMQ_USERNAME'],
            password=current_app.config['RABBITMQ_PASSWORD'],
            host=current_app.config['RABBITMQ_HOST'],
            port=current_app.config['RABBITMQ_PORT'],
            virtual_host=current_app.config['RABBITMQ_VHOST'],
            error_logger=current_app.logger,
        )
        try:
            channel = rabbitmq_connection.channel()
            channel.exchange_declare(exchange=current_app.config['SPARK_JOB_REQUEST_EXCHANGE'], exchange_type='fanout')
            channel.basic_publish(
                exchange=current_app.config['SPARK_JOB_REQUEST_EXCHANGE'],
                routing_key='',
                body=ujson.dumps(message),
                properties=pika.BasicProperties(delivery_mode=2,),
            )
        except Exception:
            # this is a relatively non critical part of LB for now, so just log the error and
            # move ahead
            current_app.logger.error('Could not send message to spark cluster: %s', ujson.dumps(message), exc_info=True)

@cli.command(name="request_user_stats")
def request_user_stats():
    """ Send a user stats request to the spark cluster
    """
    send_message_to_spark_cluster({
        'type': 'request',
        'message': 'user_stats',
    })
