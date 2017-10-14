import click
import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.stats.user as stats_user
import logging
import time

from listenbrainz import config
from listenbrainz import db
from listenbrainz import stats

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def calculate_user_stats():
    """Get the users we need to calculate our statistics for and calculate their stats.
    """

    for user in db_user.get_users_with_uncalculated_stats():

        logger.info('Calculating statistics for user %s...', user['musicbrainz_id'])

        recordings = stats_user.get_top_recordings(musicbrainz_id=user['musicbrainz_id'])
        logger.info('Top recordings for user %s done!', user['musicbrainz_id'])

        artists = stats_user.get_top_artists(musicbrainz_id=user['musicbrainz_id'])
        logger.info('Top artists for user %s done!', user['musicbrainz_id'])

        releases = stats_user.get_top_releases(musicbrainz_id=user['musicbrainz_id'])
        logger.info('Top releases for user %s done!', user['musicbrainz_id'])

        artist_count = stats_user.get_artist_count(musicbrainz_id=user['musicbrainz_id'])
        logger.info('Artist count for user %s done!', user['musicbrainz_id'])


        logger.info('Inserting calculated stats for user %s into db', user['musicbrainz_id'])
        db_stats.insert_user_stats(
            user_id=user['id'],
            artists=artists,
            recordings=recordings,
            releases=releases,
            artist_count=artist_count
        )
        logger.info('Stats calculation for user %s done!', user['musicbrainz_id'])


def calculate_stats():
    calculate_user_stats()


cli = click.Group()

@cli.command()
def calculate():
    """ Command to calculate statistics from Google BigQuery.
    This can be used from the manage.py file.
    """

    # if no bigquery support, sleep
    if not config.WRITE_TO_BIGQUERY:
        while True:
            time.sleep(10000)

    print('Connecting to Google BigQuery...')
    stats.init_bigquery_connection()
    print('Connected!')

    print('Connecting to database...')
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    print('Connected!')

    print('Calculating statistics using Google BigQuery...')
    calculate_stats()
    print('Calculations done!')
