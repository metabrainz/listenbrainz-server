import sys
from datetime import date

import click
import listenbrainz.utils as utils
import os
import pika
import ujson

from flask import current_app

from data.model.common_stat import ALLOWED_STATISTICS_RANGE
from listenbrainz.webserver import create_app


QUERIES_JSON_PATH = os.path.join(os.path.dirname(
    os.path.realpath(__file__)), 'request_queries.json')
DATAFRAME_JOB_TYPES = ("recommendation_recording", "similar_users")

cli = click.Group()


class InvalidSparkRequestError(Exception):
    pass


def _get_possible_queries():
    """ Return the dict describing all possible queries that can
    be sent to Spark. Listed in listenbrainz/spark/request_queries.json
    """
    with open(QUERIES_JSON_PATH) as f:
        return ujson.load(f)


def _prepare_query_message(query, **params):
    """ Prepare the JSON message that needs to be sent to the
    spark cluster based on the query and the parameters the
    query needs

    Args:
        query: the name of the query, should be in request_queries.json
        params: the parameters the query needs, should contain all the params
            in the corresponding request_queries.json to be valid

    Raises:
        InvalidSparkRequestError if the query isn't in the list or if the parameters
        don't match up
    """
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


def send_request_to_spark_cluster(query, **params):
    with create_app().app_context():
        message = _prepare_query_message(query, **params)

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
            channel.exchange_declare(
                exchange=current_app.config['SPARK_REQUEST_EXCHANGE'], exchange_type='fanout')
            channel.basic_publish(
                exchange=current_app.config['SPARK_REQUEST_EXCHANGE'],
                routing_key='',
                body=message,
                properties=pika.BasicProperties(delivery_mode=2,),
            )
        except Exception:
            # this is a relatively non critical part of LB for now, so just log the error and
            # move ahead
            current_app.logger.error(
                'Could not send message to spark cluster: %s', ujson.dumps(message), exc_info=True)


@cli.command(name="request_user_stats")
@click.option("--type", 'type_', type=click.Choice(['entity', 'listening_activity', 'daily_activity']),
              help="Type of statistics to calculate", required=True)
@click.option("--range", 'range_', type=click.Choice(ALLOWED_STATISTICS_RANGE),
              help="Time range of statistics to calculate", required=True)
@click.option("--entity", type=click.Choice(['artists', 'releases', 'recordings']),
              help="Entity for which statistics should be calculated")
def request_user_stats(type_, range_, entity):
    """ Send a user stats request to the spark cluster
    """
    params = {
        "stats_range": range_
    }
    if type_ == "entity" and entity:
        params["entity"] = entity

    send_request_to_spark_cluster(f"stats.user.{type_}", **params)


@cli.command(name="request_sitewide_stats")
@click.option("--type", 'type_', type=click.Choice(['entity', 'listening_activity']),
              help="Type of statistics to calculate", required=True)
@click.option("--range", 'range_', type=click.Choice(ALLOWED_STATISTICS_RANGE),
              help="Time range of statistics to calculate", required=True)
@click.option("--entity", type=click.Choice(['artists', 'releases', 'recordings']),
              help="Entity for which statistics should be calculated")
def request_sitewide_stats(type_, range_, entity):
    """ Send request to calculate sitewide stats to the spark cluster
    """
    params = {
        "stats_range": range_
    }
    if type_ == "entity" and entity:
        params["entity"] = entity

    send_request_to_spark_cluster(f"stats.sitewide.{type_}", **params)


@cli.command(name="request_yim_new_release_stats")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
def request_yim_new_release_stats(year: int):
    """ Send request to calculate new release stats to the spark cluster
    """
    send_request_to_spark_cluster("year_in_music.new_releases_of_top_artists", year=year)


@cli.command(name="request_yim_most_prominent_color")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
def request_yim_most_prominent_color(year: int):
    """ Send request to calculate most prominent color stat to the spark cluster
    """
    send_request_to_spark_cluster("year_in_music.most_prominent_color", year=year)


@cli.command(name="request_yim_day_of_week")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
def request_yim_day_of_week(year: int):
    """ Send request to calculate most listened day of week to the spark cluster
    """
    send_request_to_spark_cluster("year_in_music.day_of_week", year=year)


@cli.command(name="request_yim_most_listened_year")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
def request_yim_most_listened_year(year: int):
    """ Send request to calculate most listened year stat to the spark cluster
    """
    send_request_to_spark_cluster("year_in_music.most_listened_year", year=year)


@cli.command(name="request_yim_top_stats")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
def request_yim_top_stats(year: int):
    """ Send request to calculate top stats to the spark cluster
    """
    send_request_to_spark_cluster("year_in_music.top_stats", year=year)


@cli.command(name="request_listens_per_day")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
def request_yim_listens_per_day(year: int):
    """ Send request to calculate listens per day stat to the spark cluster
    """
    send_request_to_spark_cluster("year_in_music.listens_per_day", year=year)


@cli.command(name="request_yearly_listen_count")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
def request_yim_listen_count(year: int):
    """ Send request to calculate yearly listen count stat to the spark cluster
    """
    send_request_to_spark_cluster("year_in_music.listen_count", year=year)


@cli.command(name="request_import_full")
@click.option("--id", "id_", type=int, required=False,
              help="Optional. ID of the full dump to import, defaults to latest dump available on FTP server")
def request_import_new_full_dump(id_: int):
    """ Send the cluster a request to import a new full data dump
    """
    if id_:
        send_request_to_spark_cluster('import.dump.full_id', dump_id=id_)
    else:
        send_request_to_spark_cluster('import.dump.full_newest')


@cli.command(name="request_import_incremental")
@click.option("--id", "id_", type=int, required=False,
              help="Optional. ID of the incremental dump to import, defaults to latest dump available on FTP server")
def request_import_new_incremental_dump(id_: int):
    """ Send the cluster a request to import a new incremental data dump
    """
    if id_:
        send_request_to_spark_cluster('import.dump.incremental_id', dump_id=id_)
    else:
        send_request_to_spark_cluster('import.dump.incremental_newest')


@cli.command(name="request_dataframes")
@click.option("--days", type=int, default=180, help="Request model to be trained on data of given number of days")
@click.option("--job-type", default="recommendation_recording", help="The type of dataframes to request. 'recommendation_recording' or 'similar_users' are allowed.")
@click.option("--listens-threshold", type=int, default=0, help="The minimum number of listens a user should have to be included in the dataframes.")
def request_dataframes(days, job_type, listens_threshold):
    """ Send the cluster a request to create dataframes.
    """

    if job_type not in DATAFRAME_JOB_TYPES:
        print("job_type must be one of ", DATAFRAME_JOB_TYPES)
        sys.exit(-1)

    send_request_to_spark_cluster(
        'cf.recommendations.recording.create_dataframes', train_model_window=days,
        job_type=job_type, minimum_listens_threshold=listens_threshold
    )


def parse_list(ctx, args):
    return list(args)


@cli.command(name='request_model')
@click.option("--rank", callback=parse_list, default=[100, 120], type=int, multiple=True, help="Number of hidden features")
@click.option("--itr", callback=parse_list, default=[5, 10], type=int, multiple=True, help="Number of iterations to run.")
@click.option("--lmbda", callback=parse_list, default=[0.1, 10.0], type=float, multiple=True, help="Controls over fitting.")
@click.option("--alpha", default=3.0, type=float, help="Baseline level of confidence weighting applied.")
def request_model(rank, itr, lmbda, alpha):
    """ Send the cluster a request to train the model.

    For more details refer to https://spark.apache.org/docs/2.1.0/mllib-collaborative-filtering.html
    """
    params = {
        'ranks': rank,
        'lambdas': lmbda,
        'iterations': itr,
        'alpha': alpha,
    }

    send_request_to_spark_cluster('cf.recommendations.recording.train_model', **params)


@cli.command(name='request_candidate_sets')
@click.option("--days", type=int, default=7, help="Request recommendations to be generated on history of given number of days")
@click.option("--top", type=int, default=20, help="Calculate given number of top artist.")
@click.option("--similar", type=int, default=20, help="Calculate given number of similar artist.")
@click.option("--html", is_flag=True, default=False, help='Enable/disable HTML file generation')
@click.option("--user-name", "users", callback=parse_list, default=[], multiple=True,
              help="Generate candidate set for given users. Generate for all active users by default.")
def request_candidate_sets(days, top, similar, users, html):
    """ Send the cluster a request to generate candidate sets.
    """
    params = {
        'recommendation_generation_window': days,
        "top_artist_limit": top,
        "similar_artist_limit": similar,
        "users": users,
        "html_flag": html
    }
    send_request_to_spark_cluster('cf.recommendations.recording.candidate_sets', **params)


@cli.command(name='request_recommendations')
@click.option("--top", type=int, default=1000, help="Generate given number of top artist recommendations")
@click.option("--similar", type=int, default=1000, help="Generate given number of similar artist recommendations")
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
    send_request_to_spark_cluster('cf.recommendations.recording.recommendations', **params)


@cli.command(name='request_import_artist_relation')
def request_import_artist_relation():
    """ Send the spark cluster a request to import artist relation.
    """
    send_request_to_spark_cluster('import.artist_relation')


@cli.command(name='request_import_musicbrainz_release_dump')
def request_import_musicbrainz_release_dump():
    """ Send the spark cluster a request to import musicbrainz release dump.
    """
    send_request_to_spark_cluster('import.musicbrainz_release_dump')


@cli.command(name='request_similar_users')
@click.option("--max-num-users", type=int, default=25, help="The maxiumum number of similar users to return for any given user.")
def request_similar_users(max_num_users):
    """ Send the cluster a request to generate similar users.
    """
    send_request_to_spark_cluster('similarity.similar_users', max_num_users=max_num_users)


@cli.command(name="request_yim_similar_users")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
def request_yim_similar_users(year: int):
    """ Send the cluster a request to generate similar users for Year in Music. """
    send_request_to_spark_cluster('year_in_music.similar_users', year=year)


@cli.command(name="request_year_in_music")
@click.option("--year", type=int, help="Year for which to calculate the stat",
              default=date.today().year)
@click.pass_context
def request_year_in_music(ctx, year: int):
    """ Send the cluster a request to generate all year in music statistics. """
    ctx.invoke(request_yim_new_release_stats, year=year)
    ctx.invoke(request_yim_most_prominent_color, year=year)
    ctx.invoke(request_yim_day_of_week, year=year)
    ctx.invoke(request_yim_most_listened_year, year=year)
    ctx.invoke(request_yim_top_stats, year=year)
    ctx.invoke(request_yim_listens_per_day, year=year)
    ctx.invoke(request_yim_listen_count, year=year)
    ctx.invoke(request_yim_similar_users, year=year)


# Some useful commands to keep our crontabs manageable. These commands do not add new functionality
# rather combine multiple commands related to a task so that they are always invoked in the correct order.

@cli.command(name='cron_request_all_stats')
@click.pass_context
def cron_request_all_stats(ctx):
    for stats_range in ALLOWED_STATISTICS_RANGE:
        for entity in ["artists", "releases", "recordings"]:
            ctx.invoke(request_user_stats, type_="entity", range_=stats_range, entity=entity)

        for stat in ["listening_activity", "daily_activity"]:
            ctx.invoke(request_user_stats, type_=stat, range_=stats_range)

        for entity in ["artists", "releases", "recordings"]:
            ctx.invoke(request_sitewide_stats, type_="entity", range_=stats_range, entity=entity)

        for stat in ["listening_activity"]:
            ctx.invoke(request_sitewide_stats, type_=stat, range_=stats_range)


@cli.command(name='cron_request_similar_users')
@click.pass_context
def cron_request_similar_users(ctx):
    ctx.invoke(request_dataframes, job_type="similar_users", days=365, listens_threshold=50)
    ctx.invoke(request_similar_users)


@cli.command(name='cron_request_recommendations')
@click.pass_context
def cron_request_recommendations(ctx):
    ctx.invoke(request_dataframes)
    ctx.invoke(request_model)
    ctx.invoke(request_candidate_sets)
    ctx.invoke(request_recommendations, top=1000, similar=1000)
