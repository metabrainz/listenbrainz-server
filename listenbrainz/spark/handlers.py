""" This file contains handler functions for rabbitmq messages we
receive from the Spark cluster.
"""
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats

from flask import current_app, render_template
from brainzutils.mail import send_mail
from datetime import datetime, timezone, timedelta

TIME_TO_CONSIDER_STATS_AS_OLD = 12 # hours

def is_new_user_stats_batch():
    """ Returns True if this batch of user stats is new, False otherwise

    User stats come in as multiple rabbitmq messages. We only wish to send an email once per batch.
    So, we check the database and see if the difference between the last time stats were updated
    and right now is greater than 12 hours.
    """
    return datetime.now(timezone.utc) - db_stats.get_timestamp_for_last_user_stats_update() > timedelta(hours=TIME_TO_CONSIDER_STATS_AS_OLD)


def notify_user_stats_update():
    if not current_app.config['TESTING']:
        send_mail(
            subject="New user stats are being written into the DB - ListenBrainz",
            text=render_template('emails/user_stats_notification.txt', now=str(datetime.utcnow())),
            recipients=['listenbrainz-observability@metabrainz.org'],
            from_name='ListenBrainz',
            from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN']
        )


def handle_user_artist(data):
    """ Take artist stats for a user and save it in the database.
    """
    musicbrainz_id = data['musicbrainz_id']
    user = db_user.get_by_mb_id(musicbrainz_id)
    if not user:
        return

    # send a notification if this is a new batch of stats
    if is_new_user_stats_batch():
        notify_user_stats_update()
    artists = data['artist_stats']
    artist_count = data['artist_count']
    db_stats.insert_user_stats(user['id'], artists, {}, {}, artist_count)


def handle_dump_imported(data):
    """ Process the response that the cluster sends after importing a new full dump

    We don't really need to _do_ anything, just send an email over for observability.
    """
    if current_app.config['TESTING']:
        return


    dump_name = data['imported_dump']
    import_completion_time = data['time']
    send_mail(
        subject='A full data dump has been imported into the Spark cluster',
        text=render_template('emails/dump_import_notification.txt', dump_name=dump_name, time=import_completion_time),
        recipients=['listenbrainz-observability@metabrainz.org'],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )
