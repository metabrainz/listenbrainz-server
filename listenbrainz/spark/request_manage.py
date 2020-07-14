import sys
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
@click.option("--type", 'type_', type=click.Choice(['entity', 'listening_activity']),
              help="Type of statistics to calculate", required=True)
@click.option("--range", 'range_', type=click.Choice(['week', 'month', 'year', 'all_time']),
              help="Time range of statistics to calculate", required=True)
@click.option("--entity", type=click.Choice(['artists', 'releases', 'recordings']),
              help="Entity for which statistics should be calculated")
def request_user_stats(type_, range_, entity):
    """ Send a user stats request to the spark cluster
    """
    params = {}
    if type_ == 'entity' and entity:
        params['entity'] = entity
    try:
        send_request_to_spark_cluster(_prepare_query_message(
            'stats.user.{type}.{range}'.format(range=range_, type=type_), params=params))
    except InvalidSparkRequestError:
        click.echo("Incorrect arguments provided")


@cli.command(name="request_import_full")
@click.option("--id", "id_", type=int, required=False,
              help="Optional. ID of the full dump to import, defaults to latest dump available on FTP server")
def request_import_new_full_dump(id_: int):
    """ Send the cluster a request to import a new full data dump
    """
    if id_:
        send_request_to_spark_cluster(_prepare_query_message('import.dump.full_id', params={'id': id_}))
    else:
        send_request_to_spark_cluster(_prepare_query_message('import.dump.full_newest'))


@cli.command(name="request_dataframes")
@click.option("--days", type=int, default=180, help="Request model to be trained on data of given number of days")
def request_dataframes(days):
    """ Send the cluster a request to create dataframes.
    """
    params = {
        'train_model_window': days,
    }
    send_request_to_spark_cluster(_prepare_query_message('cf_recording.recommendations.create_dataframes', params=params))


def parse_list(ctx, args):
    return list(args)


@cli.command(name='request_model')
@click.option("--rank", callback=parse_list, default=[5, 10], type=int, multiple=True, help="Number of hidden features")
@click.option("--itr", callback=parse_list, default=[5, 10], type=int, multiple=True, help="Number of iterations to run.")
@click.option("--lmbda", callback=parse_list, default=[0.1, 10.0], type=float, multiple=True, help="Controls over fitting.")
@click.option("--alpha", default=3.0, type=float, help="Baseline level of confidence weighting applied.")
def request_model(rank, itr, lmbda, alpha):
    """ Send the cluster a request to train the model.
        For more details refer to 'https://spark.apache.org/docs/2.1.0/mllib-collaborative-filtering.html'
    """
    params = {
        'ranks': rank,
        'lambdas': lmbda,
        'iterations': itr,
        'alpha': alpha,
    }

    send_request_to_spark_cluster(_prepare_query_message('cf_recording.recommendations.train_model', params=params))


@cli.command(name='request_candidate_sets')
@click.option("--days", type=int, default=7, help="Request recommendations to be generated on history of given number of days")
@click.option("--top", type=int, default=20, help="Calculate given number of top artist.")
@click.option("--similar", type=int, default=20, help="Calculate given number of similar artist.")
@click.option("--user-name", "users", callback=parse_list, default=[], multiple=True,
              help="Generate candidate set for given users. Generate for all active users by default.")
def request_candidate_sets(days, top, similar, users):
    """ Send the cluster a request to generate candidate sets.
    """
    params = {
        'recommendation_generation_window': days,
        "top_artist_limit": top,
        "similar_artist_limit": similar,
        "users": users
    }
    send_request_to_spark_cluster(_prepare_query_message('cf_recording.recommendations.candidate_sets', params=params))


@cli.command(name='request_recommendations')
@click.option("--top", type=int, default=200, help="Generate given number of top artist recommendations")
@click.option("--similar", type=int, default=200, help="Generate given number of similar artist recommendations")
@click.option("--user-name", 'users', callback=parse_list, default=[], multiple=True,
              help="Generate recommendations for given users. Generate recommendations for all users by default.")
def request_recommendations(top, similar, users):
    """ Send the cluster a request to generate recommendations.
    """
    params = {
        'recommendation_top_artist_limit': top,
        'recommendation_similar_artist_limit': similar,
        'users': users
    }
    send_request_to_spark_cluster(_prepare_query_message('cf_recording.recommendations.recommend', params=params))


@cli.command(name='request_import_mapping')
def request_import_mapping():
    """ Send the spark cluster a request to import msid mbid mapping.
    """

    send_request_to_spark_cluster(_prepare_query_message('import.mapping'))


@cli.command(name='request_import_artist_relation')
def request_import_artist_relation():
    """ Send the spark cluster a request to import artist relation.
    """

    send_request_to_spark_cluster(_prepare_query_message('import.artist_relation'))
