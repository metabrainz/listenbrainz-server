import click
import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.stats.user as stats_user
import listenbrainz.utils as utils
import logging
import pika
import sys
import time
import ujson

from listenbrainz import config
from listenbrainz import db
from listenbrainz import stats

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def push_users_to_queue(channel, force=False):
    """ Get users from the db whose stats haven't been calculated and push
        them into the queue.

        Args:
            channel: the RabbitMQ channel in which we should publish the user data
    """
    logger.info('pushing users to stats calculation queue...')
    if force:
        users = db_user.get_all_users()
    else:
        users = db_user.get_users_with_uncalculated_stats()

    for user in users:
        data = {
            'type': 'user',
            'id': user['id'],
            'musicbrainz_id': user['musicbrainz_id']
        }

        channel.basic_publish(
            exchange=config.BIGQUERY_EXCHANGE,
            routing_key='',
            body=ujson.dumps(data),
            properties=pika.BasicProperties(delivery_mode = 2,),
        )
    logger.info('pushed %d users!', len(users))


def push_entities_to_queue(force=False):
    """ Creates a RabbitMQ connection and uses it to push entities which
        need their stats calculated into the queue.
    """
    rabbitmq_connection = utils.connect_to_rabbitmq(
        username=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
        host=config.RABBITMQ_HOST,
        port=config.RABBITMQ_PORT,
        virtual_host=config.RABBITMQ_VHOST,
    )
    channel = rabbitmq_connection.channel()
    channel.exchange_declare(exchange=config.BIGQUERY_EXCHANGE, exchange_type='fanout')
    push_users_to_queue(channel, force)


cli = click.Group()

@cli.command(name="populate_queue")
@click.option('--force', '-f', is_flag=True, help='Force statistics calculation for ALL entities')
def populate_queue(force):
    """ Populate the ListenBrainz stats calculation queue with entities
        which need their stats calculated.
    """
    logger.info('Connecting to database...')
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    logger.info('Connected!')

    logger.info('Pushing entities whose stats should be calculated into the queue...')
    push_entities_to_queue(force=force)
    logger.info('Pushed all relevant entities, stats_calculator should calculate stats soon!')
