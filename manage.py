import os
import sys
import click
import logging
import time

import listenbrainz_spark
from listenbrainz_spark import path
from listenbrainz_spark import utils
from listenbrainz_spark import config
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.data import import_dump

from hdfs.util import HdfsError
from py4j.protocol import Py4JJavaError

app = utils.create_app(debug=True)

@click.group()
def cli():
    pass

@cli.command(name='init_dir')
@click.option('--rm', is_flag=True, help='Delete existing directories from HDFS.')
@click.option('--recursive', is_flag=True, help='Delete existing directories from HDFS recursively.')
@click.option('--create_dir', is_flag=True, help='Create directories in HDFS.')
def init_dir(rm, recursive, create_dir):
    """ Create directories in HDFS to run the recommendation engine.
    """
    try:
        listenbrainz_spark.init_spark_session('Manage Directories')
    except Py4JJavaError as err:
        logging.error('{}\n{}\nAborting...'.format(str(err), err.java_exception))
        sys.exit(-1)

    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    if rm:
        try:
            utils.delete_dir(path.RECOMMENDATION_PARENT_DIR)
            utils.delete_dir(path.CHECKPOINT_DIR)
            logging.info('Successfully deleted directories.')
        except HdfsError as err:
            logging.error('{}: Some/all directories are non-empty. Try "--recursive" to delete recursively.'.format(
                type(err).__name__))
            logging.warning('Deleting directory recursively will delete all the recommendation data.')
            sys.exit(-1)

    if recursive:
        try:
            utils.delete_dir(path.RECOMMENDATION_PARENT_DIR, recursive=True)
            utils.delete_dir(path.CHECKPOINT_DIR, recursive=True)
            logging.info('Successfully deleted directories recursively.')
        except HdfsError as err:
            logging.error('{}: An error occurred while deleting directories recursively.\n{}\nAborting...'.format(
                type(err).__name__, str(err)))
            sys.exit(-1)

    if create_dir:
        try:
            logging.info('Creating directory to store dataframes...')
            utils.create_dir(path.DATAFRAME_DIR)

            logging.info('Creating directory to store models...')
            utils.create_dir(path.MODEL_DIR)

            logging.info('Creating directory to store candidate sets...')
            utils.create_dir(path.CANDIDATE_SET_DIR)

            logging.info('Creating directory to store RDD checkpoints...')
            utils.create_dir(path.CHECKPOINT_DIR)

            print('Done!')
        except HdfsError as err:
            logging.error('{}: An error occured while creating some/more directories.\n{}\nAborting...'.format(
                type(err).__name__, str(err)))
            sys.exit(-1)

@cli.command(name='dataframe')
def dataframes():
    """ Invoke script responsible for pre-processing data.
    """
    from listenbrainz_spark.recommendations import create_dataframes
    with app.app_context():
        create_dataframes.main()

@cli.command(name='model')
def model():
    """ Invoke script responsible for training data.
    """
    from listenbrainz_spark.recommendations import train_models
    with app.app_context():
        train_models.main()

@cli.command(name='candidate')
def candidate():
    """ Invoke script responsible for generating candidate sets.
    """
    from listenbrainz_spark.recommendations import candidate_sets
    with app.app_context():
        candidate_sets.main()

@cli.command(name='recommend')
def recommend():
    """ Invoke script responsible for generating recommendations.
    """
    from listenbrainz_spark.recommendations import recommend
    with app.app_context():
        recommend.main()

@cli.command(name='user')
def user():
    """ Invoke script responsible for calculating user statistics.
    """
    from listenbrainz_spark.stats import user
    with app.app_context():
        user.main()

@cli.command(name='request_consumer')
def request_consumer():
    """ Invoke script responsible for the request consumer
    """
    from listenbrainz_spark.request_consumer.request_consumer import main
    with app.app_context():
        main('request-consumer-%s' % str(int(time.time())))

@cli.command(name="import")
@click.argument('filename', type=click.Path(exists=True))
def import_dump_command(filename):
    import_dump.main(app_name='import', archive=filename)


@cli.resultcallback()
def remove_zip(result, **kwargs):
    """ Remove zip created by spark-submit.
    """
    os.remove(os.path.join('/', 'rec', 'listenbrainz_spark.zip'))

if __name__ == '__main__':
    # The root logger always defaults to WARNING level
    # The level is changed from WARNING to INFO
    logging.getLogger().setLevel(logging.INFO)
    cli()
