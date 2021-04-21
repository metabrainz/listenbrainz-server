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

from hdfs.util import HdfsError
from py4j.protocol import Py4JJavaError


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


@cli.command(name='upload_mapping')
def upload_mapping():
    """ Invoke script to upload mapping to HDFS.
    """
    from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader
    from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
    downloader_obj = ListenbrainzDataDownloader()
    src, _ = downloader_obj.download_msid_mbid_mapping(path.FTP_FILES_PATH)
    uploader_obj = ListenbrainzDataUploader()
    uploader_obj.upload_mapping(src)


@cli.command(name='upload_listens')
@click.option('--incremental', '-i', is_flag=True, default=False, help="Use a smaller dump (more for testing purposes)")
@click.option("--overwrite", "-o", is_flag=True, help="Deletes existing listens.")
@click.option("--id", default=None, type=int, help="Get a specific dump based on index")
def upload_listens(overwrite, incremental, id):
    """ Invoke script to upload listens to HDFS.
    """
    from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader
    from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
    downloader_obj = ListenbrainzDataDownloader()
    dump_type = 'incremental' if incremental else 'full'
    src, _, _ = downloader_obj.download_listens(directory=path.FTP_FILES_PATH, listens_dump_id=id, dump_type=dump_type)
    uploader_obj = ListenbrainzDataUploader()
    uploader_obj.upload_listens(src, overwrite=overwrite)


@cli.command(name='upload_artist_relation')
def upload_artist_relation():
    """ Invoke script  to upload artist relation to HDFS.
    """
    from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader
    from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
    downloader_obj = ListenbrainzDataDownloader()
    src, _ = downloader_obj.download_artist_relation(path.FTP_FILES_PATH)
    uploader_obj = ListenbrainzDataUploader()
    uploader_obj.upload_artist_relation(src)


@cli.command(name='dataframe')
@click.option("--days", type=int, default=180, help="Request model to be trained on data of given number of days")
def dataframes(days):
    """ Invoke script responsible for pre-processing data.
    """
    from listenbrainz_spark.recommendations.recording import create_dataframes
    _ = create_dataframes.main(train_model_window=days, job_type="recommendations")


def parse_list(ctx, args):
    return list(args)


@cli.command(name='model')
@click.option("--rank", callback=parse_list, default=[5, 10], type=int, multiple=True, help="Number of hidden features")
@click.option("--itr", callback=parse_list, default=[5, 10], type=int, multiple=True, help="Number of iterations to run.")
@click.option("--lmbda", callback=parse_list, default=[0.1, 10.0], type=float, multiple=True, help="Controls over fitting.")
@click.option("--alpha", default=3.0, type=float, help="Baseline level of confidence weighting applied.")
def model(rank, itr, lmbda, alpha):
    """ Invoke script responsible for training data.
        For more details refer to 'https://spark.apache.org/docs/2.1.0/mllib-collaborative-filtering.html'
    """
    from listenbrainz_spark.recommendations.recording import train_models
    _ = train_models.main(ranks=rank, lambdas=lmbda, iterations=itr, alpha=alpha)


@cli.command(name='candidate')
@click.option("--days", type=int, default=7, help="Request recommendations to be generated on history of given number of days")
@click.option("--top", type=int, default=20, help="Calculate given number of top artist.")
@click.option("--similar", type=int, default=20, help="Calculate given number of similar artist.")
@click.option("--html", is_flag=True, default=False, help='Enable/disable HTML file generation')
@click.option("--user-name", "users", callback=parse_list, default=[], multiple=True,
              help="Generate candidate set for given users. Generate for all active users by default.")
def candidate(days, top, similar, users, html):
    """ Invoke script responsible for generating candidate sets.
    """
    from listenbrainz_spark.recommendations.recording import candidate_sets
    _ = candidate_sets.main(recommendation_generation_window=days, top_artist_limit=top,
                            similar_artist_limit=similar, users=users, html_flag=html)


@cli.command(name='recommend')
@click.option("--top", type=int, default=200, help="Generate given number of top artist recommendations")
@click.option("--similar", type=int, default=200, help="Generate given number of similar artist recommendations")
@click.option("--user-name", 'users', callback=parse_list, default=[], multiple=True,
              help="Generate recommendations for given users. Generate recommendations for all users by default.")
def recommend(top, similar, users):
    """ Invoke script responsible for generating recommendations.
    """
    from listenbrainz_spark.recommendations.recording import recommend
    _ = recommend.main(recommendation_top_artist_limit=top, recommendation_similar_artist_limit=similar, users=users)


@cli.command(name='user')
def user():
    """ Invoke script responsible for calculating user statistics.
    """
    from listenbrainz_spark.stats import user
    user.main()


@cli.command(name='request_consumer')
def request_consumer():
    """ Invoke script responsible for the request consumer
    """
    from listenbrainz_spark.request_consumer.request_consumer import main
    main('request-consumer-%s' % str(int(time.time())))


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
