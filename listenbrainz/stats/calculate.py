import click
import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.stats.user as stats_user
import logging
import sys
import time

from listenbrainz import default_config as config
try:
    from listenbrainz import custom_config as config
except ImportError:
    pass
from listenbrainz import db
from listenbrainz import stats

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def calculate_user_stats(force=False):
    """Get the users we need to calculate our statistics for and calculate their stats.
    """

    logger.info('Beginning calculation of user stats...')

    while True:
        try:
            if force:
                users = db_user.get_all_users()
            else:
                users = db_user.get_users_with_uncalculated_stats()
            break
        except Exception as e:
            logger.error('Error while getting user list for stats calculation: %s', str(e))
            logger.error('Going to sleep for 3 seconds and then try again...')
            time.sleep(3)

    total = len(users)
    done = 0
    failed = 0

    for user in users:

        logger.info('Calculating statistics for user %s...', user['musicbrainz_id'])
        try:
            recordings = stats_user.get_top_recordings(musicbrainz_id=user['musicbrainz_id'])
            logger.info('Top recordings for user %s done!', user['musicbrainz_id'])

            artists = stats_user.get_top_artists(musicbrainz_id=user['musicbrainz_id'])
            logger.info('Top artists for user %s done!', user['musicbrainz_id'])

            releases = stats_user.get_top_releases(musicbrainz_id=user['musicbrainz_id'])
            logger.info('Top releases for user %s done!', user['musicbrainz_id'])

            artist_count = stats_user.get_artist_count(musicbrainz_id=user['musicbrainz_id'])
            logger.info('Artist count for user %s done!', user['musicbrainz_id'])

        except Exception as e:
            logger.error('Unable to calculate stats for user %s. :(', user['musicbrainz_id'])
            logger.error('Giving up for now...')
            failed += 1
            continue

        logger.info('Inserting calculated stats for user %s into db', user['musicbrainz_id'])
        while True:
            try:
                db_stats.insert_user_stats(
                    user_id=user['id'],
                    artists=artists,
                    recordings=recordings,
                    releases=releases,
                    artist_count=artist_count
                )
                logger.info('Stats calculation for user %s done!', user['musicbrainz_id'])
                break

            except Exception as e:
                logger.error('Unable to insert calculated stats into db for user %s', user['musicbrainz_id'])
                logger.error('Error: %s', str(e))
                logger.error('Going to sleep and trying again...')
                time.sleep(3)

        done += 1


    logger.info('User statistics calculations done!')
    logger.info('Total users: %d', total)
    logger.info('Successfully calculated stats for %d users', done)
    logger.info('Stats calculation failed for %d users', failed)


def calculate_stats(force=False):
    calculate_user_stats(force)


cli = click.Group()

@cli.command()
@click.option('--force', '-f', is_flag=True, help='Force statistics calculation for ALL users')
def calculate(force):
    """ Command to calculate statistics from Google BigQuery.
    This can be used from the manage.py file.
    """

    # if no bigquery support, sleep
    if not config.WRITE_TO_BIGQUERY:
        while True:
            time.sleep(10000)

    logger.info('Connecting to Google BigQuery...')
    stats.init_bigquery_connection()
    logger.info('Connected!')

    logger.info('Connecting to database...')
    db.init_db_connection(config.SQLALCHEMY_DATABASE_URI)
    logger.info('Connected!')

    logger.info('Calculating statistics using Google BigQuery...')
    calculate_stats(force=force)
    logger.info('Calculations done!')
