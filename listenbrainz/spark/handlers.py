""" This file contains handler functions for rabbitmq messages we
receive from the Spark cluster.
"""
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats

from flask import current_app, render_template
from brainzutils.mail import send_mail
from datetime import datetime, timezone, timedelta

TIME_TO_CONSIDER_STATS_AS_OLD = 12  # hours


def is_new_user_stats_batch():
    """ Returns True if this batch of user stats is new, False otherwise

    User stats come in as multiple rabbitmq messages. We only wish to send an email once per batch.
    So, we check the database and see if the difference between the last time stats were updated
    and right now is greater than 12 hours.
    """
    last_update_ts = db_stats.get_timestamp_for_last_user_stats_update()
    if last_update_ts is None:
        last_update_ts = datetime.min.replace(tzinfo=timezone.utc)  # use min datetime value if last_update_ts is None

    return datetime.now(timezone.utc) - last_update_ts > timedelta(hours=TIME_TO_CONSIDER_STATS_AS_OLD)


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
        current_app.logger.critical("Calculated stats for a user that doesn't exist in the Postgres database: %s", musicbrainz_id)
        return

    # send a notification if this is a new batch of stats
    if is_new_user_stats_batch():
        notify_user_stats_update()
    current_app.logger.debug("inserting stats for user %s", musicbrainz_id)

    to_remove = {'musicbrainz_id', 'type'}
    data_mod = {key: data[key] for key in data if key not in to_remove}

    db_stats.insert_user_stats(user['id'], data_mod, {}, {})


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
