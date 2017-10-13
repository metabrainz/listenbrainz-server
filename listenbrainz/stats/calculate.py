import click
import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.stats.user as stats_user
import time

from listenbrainz import db
from listenbrainz import config
from listenbrainz import stats


def calculate_user_stats():
    for user in db_user.get_recently_logged_in_users():
        recordings = stats_user.get_top_recordings(musicbrainz_id=user['musicbrainz_id'])
        artists = stats_user.get_top_artists(musicbrainz_id=user['musicbrainz_id'])
        releases = stats_user.get_top_releases(musicbrainz_id=user['musicbrainz_id'])
        artist_count = stats_user.get_artist_count(musicbrainz_id=user['musicbrainz_id'])

        db_stats.insert_user_stats(
            user_id=user['id'],
            artists=artists,
            recordings=recordings,
            releases=releases,
            artist_count=artist_count
        )

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
