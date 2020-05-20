import click
import listenbrainz.utils as utils
import os
import pika
import ujson

from flask import current_app
from listenbrainz.webserver import create_app


QUERIES_JSON_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'request_queries.json')

cli = click.Group()


class InvalidSparkRequestError(Exception):
    pass


def _get_possible_queries():
    """ Return the dict describing all possible queries that can
    be sent to Spark. Listed in listenbrainz/spark/request_queries.json
    """
    with open(QUERIES_JSON_PATH) as f:
        return ujson.load(f)


def _prepare_query_message(query, params=None):
    """ Prepare the JSON message that needs to be sent to the
    spark cluster based on the query and the parameters the
    query needs

    Args:
        query (str): the name of the query, should be in request_queries.json
        params (dict): the parameters the query needs, should contain all the params
            in the correspoding request_queries.json to be valid

    Raises:
        InvalidSparkRequestError if the query isn't in the list or if the parameters
        don't match up
    """
    if params is None:
        params = {}

    possible_queries = _get_possible_queries()
    if query not in possible_queries:
        raise InvalidSparkRequestError(query)

    message = {'query': possible_queries[query]['name']}
    required_params = set(possible_queries[query]['params'])
    given_params = set(params.keys())
    if required_params != given_params:
        raise InvalidSparkRequestError

    if params:
        message['params'] = {}
        for key, value in params.items():
            message['params'][key] = value

    return ujson.dumps(message)


def send_request_to_spark_cluster(message):
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
            channel.exchange_declare(exchange=current_app.config['SPARK_REQUEST_EXCHANGE'], exchange_type='fanout')
            channel.basic_publish(
                exchange=current_app.config['SPARK_REQUEST_EXCHANGE'],
                routing_key='',
                body=message,
                properties=pika.BasicProperties(delivery_mode=2,),
            )
        except Exception:
            # this is a relatively non critical part of LB for now, so just log the error and
            # move ahead
            current_app.logger.error('Could not send message to spark cluster: %s', ujson.dumps(message), exc_info=True)


@cli.command(name="request_user_stats")
@click.option("--week", is_flag=True, help="Request weekly statistics")
@click.option("--month", is_flag=True, help="Request monthly statistics")
@click.option("--year", is_flag=True, help="Request yearly statistics")
@click.option("--all-time", is_flag=True, help="Request all time statistics")
def request_user_stats(week, month, year, all_time):
    """ Send a user stats request to the spark cluster
    """
    if week:
        send_request_to_spark_cluster(_prepare_query_message('stats.user.artist.week'))
        return

    if month:
        send_request_to_spark_cluster(_prepare_query_message('stats.user.artist.month'))
        return

    if year:
        send_request_to_spark_cluster(_prepare_query_message('stats.user.artist.year'))
        return

    if all_time:
        send_request_to_spark_cluster(_prepare_query_message('stats.user.artist.all_time'))
        return

    # Default if no specific flag is provided
    send_request_to_spark_cluster(_prepare_query_message('stats.user.all'))


@cli.command(name="request_import_full")
def request_import_new_full_dump():
    """ Send the cluster a request to import a new full data dump
    """
    send_request_to_spark_cluster(_prepare_query_message('import.dump.full'))


@cli.command(name="request_dataframes")
def request_dataframes():
    """ Send the cluster a request to create dataframes.
    """
    send_request_to_spark_cluster(_prepare_query_message('cf_recording.recommendations.create_dataframes'))


@cli.command(name='request_model')
def request_model():
    """ Send the cluster a request to train the model.
    """
    send_request_to_spark_cluster(_prepare_query_message('cf_recording.recommendations.train_model'))


@cli.command(name='request_candidate_sets')
def request_candidate_sets():
    """ Send the cluster a request to generate candidate sets.
    """
    send_request_to_spark_cluster(_prepare_query_message('cf_recording.recommendations.candidate_sets'))


@cli.command(name='request_recommendations')
def request_recommendations():
    """ Send the cluster a request to generate recommendations.
    """
    send_request_to_spark_cluster(_prepare_query_message('cf_recording.recommendations.recommend'))
