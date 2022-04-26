""" This file contains handler functions for rabbitmq messages we
    receive from the Spark cluster.
"""
import json
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
import listenbrainz.db.missing_musicbrainz_data as db_missing_musicbrainz_data
from listenbrainz.db import year_in_music

from flask import current_app, render_template
from pydantic import ValidationError
from brainzutils.mail import send_mail
from datetime import datetime, timezone, timedelta

from data.model.common_stat import StatRange
from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataJson
from data.model.user_cf_recommendations_recording_message import UserRecommendationsJson
from listenbrainz.db.recording_discovery import insert_recording_discovery
from listenbrainz.db.similar_users import import_user_similarities
from listenbrainz.spark.troi_bot import run_post_recommendation_troi_bot


TIME_TO_CONSIDER_STATS_AS_OLD = 20  # minutes
TIME_TO_CONSIDER_RECOMMENDATIONS_AS_OLD = 7  # days


def is_new_user_stats_batch():
    """ Returns True if this batch of user stats is new, False otherwise

    User stats come in as multiple rabbitmq messages. We only wish to send an email once per batch.
    So, we check the database and see if the difference between the last time stats were updated
    and right now is greater than 12 hours.
    """
    last_update_ts = db_stats.get_timestamp_for_last_user_stats_update()
    if last_update_ts is None:
        last_update_ts = datetime.min.replace(tzinfo=timezone.utc)  # use min datetime value if last_update_ts is None

    return datetime.now(timezone.utc) - last_update_ts > timedelta(minutes=TIME_TO_CONSIDER_STATS_AS_OLD)


def notify_user_stats_update(stat_type):
    if not current_app.config['TESTING']:
        send_mail(
            subject="New user stats are being written into the DB - ListenBrainz",
            text=render_template('emails/user_stats_notification.txt', now=str(datetime.utcnow()), stat_type=stat_type),
            recipients=['listenbrainz-observability@metabrainz.org'],
            from_name='ListenBrainz',
            from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN']
        )


def handle_recording_discovery(data):
    insert_recording_discovery(data["data"])


def handle_user_entity(data):
    """ Take entity stats for a user and save it in the database. """
    values = [(entry["user_id"], entry["count"], json.dumps(entry["data"])) for entry in data["data"]]
    db_stats.insert_multiple_user_jsonb_data(
        data["entity"],
        data["stats_range"],
        data["from_ts"],
        data["to_ts"],
        values
    )


def _handle_user_activity_stats(stats_type, data):
    values = [(entry["user_id"], 0, json.dumps(entry["data"])) for entry in data["data"]]
    db_stats.insert_multiple_user_jsonb_data(
        stats_type,
        data["stats_range"],
        data["from_ts"],
        data["to_ts"],
        values
    )


def handle_user_listening_activity(data):
    """ Take listening activity stats for user and save it in database. """
    _handle_user_activity_stats("listening_activity", data)


def handle_user_daily_activity(data):
    """ Take daily activity stats for user and save it in database. """
    _handle_user_activity_stats("daily_activity", data)


def handle_sitewide_entity(data):
    """ Take sitewide entity stats and save it in the database. """
    # send a notification if this is a new batch of stats
    if is_new_user_stats_batch():
        notify_user_stats_update(stat_type=data.get('type', ''))

    stats_range = data['stats_range']
    entity = data['entity']

    try:
        db_stats.insert_sitewide_jsonb_data(entity, StatRange[EntityRecord](**data))
    except ValidationError:
        current_app.logger.error(f"""ValidationError while inserting {stats_range} sitewide top {entity}.
        Data: {json.dumps(data, indent=3)}""", exc_info=True)


def handle_sitewide_listening_activity(data):
    db_stats.insert_sitewide_jsonb_data("listening_activity", StatRange[ListeningActivityRecord](**data))


def handle_dump_imported(data):
    """ Process the response that the cluster sends after importing a new dump

    We don't really need to _do_ anything, just send an email over if there was an error.
    """
    if current_app.config['TESTING']:
        return

    errors = data['errors']
    import_completion_time = data['time']

    if errors:
        send_mail(
            subject='Spark Cluster Dump import failures!',
            text=render_template('emails/dump_import_failure.txt', errors=errors, time=import_completion_time),
            recipients=['listenbrainz-exceptions@metabrainz.org'],
            from_name='ListenBrainz',
            from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
        )


def handle_dataframes(data):
    """ Send an email after dataframes have been successfully created and uploaded to HDFS.
    """
    if current_app.config['TESTING']:
        return

    dataframe_upload_time = data['dataframe_upload_time']
    dataframe_creation_time = data['total_time']
    from_date = data['from_date']
    to_date = data['to_date']
    send_mail(
        subject='Dataframes have been uploaded to HDFS',
        text=render_template('emails/cf_recording_dataframes_upload_notification.txt', time_to_upload=dataframe_upload_time,
                             from_date=from_date, to_date=to_date, total_time=dataframe_creation_time),
        recipients=['listenbrainz-observability@metabrainz.org'],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )


def handle_missing_musicbrainz_data(data):
    """ Insert user missing musicbrainz data i.e data submitted to ListenBrainz but not MusicBrainz.
    """
    user_id = data['user_id']
    user = db_user.get(user_id)

    if not user:
        return

    current_app.logger.debug(f"Inserting missing musicbrainz data for {user['musicbrainz_id']}")

    missing_musicbrainz_data = data['missing_musicbrainz_data']
    source = data['source']

    try:
        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            user['id'],
            UserMissingMusicBrainzDataJson(missing_musicbrainz_data=missing_musicbrainz_data),
            source
        )
    except ValidationError:
        current_app.logger.error(f"""
        ValidationError while inserting missing MusicBrainz data from source "{source}" for user with musicbrainz_id:
         {user["musicbrainz_id"]}. Data: {json.dumps(data, indent=3)}""", exc_info=True)

    current_app.logger.debug(f"Missing musicbrainz data for {user['musicbrainz_id']} inserted")


def handle_model(data):
    """ Send an email after trained data (model) has been successfully uploaded to HDFS.
    """
    if current_app.config['TESTING']:
        return

    model_upload_time = data['model_upload_time']
    model_creation_time = data['total_time']
    send_mail(
        subject='Model created and successfully uploaded to HDFS',
        text=render_template('emails/cf_recording_model_upload_notification.txt', time_to_upload=model_upload_time,
                             total_time=model_creation_time),
        recipients=['listenbrainz-observability@metabrainz.org'],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )


def handle_candidate_sets(data):
    """ Send an email after candidate sets have been successfully uploaded to HDFS.
    """
    if current_app.config['TESTING']:
        return

    candidate_sets_upload_time = data['candidate_sets_upload_time']
    candidate_set_creation_time = data['total_time']
    from_date = data['from_date']
    to_date = data['to_date']
    send_mail(
        subject='Candidate sets created and successfully uploaded to HDFS',
        text=render_template('emails/cf_candidate_sets_upload_notification.txt', time_to_upload=candidate_sets_upload_time,
                             from_date=from_date, to_date=to_date, total_time=candidate_set_creation_time),
        recipients=['listenbrainz-observability@metabrainz.org'],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )


def handle_recommendations(data):
    """ Take recommended recordings for a user and save it in the db.
    """
    user_id = data['user_id']
    user = db_user.get(user_id)
    if not user:
        current_app.logger.info(f"Generated recommendations for a user that doesn't exist in the Postgres database: {user_id}")
        return

    current_app.logger.debug("inserting recommendation for {}".format(user["musicbrainz_id"]))
    recommendations = data['recommendations']

    try:
        db_recommendations_cf_recording.insert_user_recommendation(
            user_id,
            UserRecommendationsJson(**recommendations)
        )
    except ValidationError:
        current_app.logger.error(f"""ValidationError while inserting recommendations for user with musicbrainz_id:
                                 {user["musicbrainz_id"]}. \nData: {json.dumps(data, indent=3)}""")

    current_app.logger.debug("recommendation for {} inserted".format(user["musicbrainz_id"]))

    current_app.logger.debug("Running post recommendation steps for user {}".format(user["musicbrainz_id"]))
    run_post_recommendation_troi_bot(user["musicbrainz_id"])


def notify_mapping_import(data):
    """ Send an email after msid mbid mapping has been successfully imported into the cluster.
    """
    if current_app.config['TESTING']:
        return

    mapping_name = data['imported_mapping']
    import_time = data['import_time']
    time_taken_to_import = data['time_taken_to_import']

    send_mail(
        subject='MSID MBID mapping has been imported into the Spark cluster',
        text=render_template('emails/mapping_import_notification.txt', mapping_name=mapping_name, import_time=import_time,
                             time_taken_to_import=time_taken_to_import),
        recipients=['listenbrainz-observability@metabrainz.org'],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )


def notify_artist_relation_import(data):
    """ Send an email after artist relation has been sucessfully imported into the cluster.
    """
    if current_app.config['TESTING']:
        return

    artist_relation_name = data['imported_artist_relation']
    import_time = data['import_time']
    time_taken_to_import = data['time_taken_to_import']

    send_mail(
        subject='Artist relation has been imported into the Spark cluster',
        text=render_template('emails/artist_relation_import_notification.txt',
                             artist_relation_name=artist_relation_name, import_time=import_time,
                             time_taken_to_import=time_taken_to_import),
        recipients=['listenbrainz-observability@metabrainz.org'],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )


def notify_cf_recording_recommendations_generation(data):
    """
    Send an email to notify recommendations have been generated and are being written into db.
    """
    if current_app.config['TESTING']:
        return

    active_user_count = data['active_user_count']
    total_time = data['total_time']
    top_artist_user_count = data['top_artist_user_count']
    similar_artist_user_count = data['similar_artist_user_count']
    send_mail(
        subject='Recommendations have been generated and pushed to the queue.',
        text=render_template('emails/cf_recording_recommendation_notification.txt',
                             active_user_count=active_user_count, total_time=total_time,
                             top_artist_user_count=top_artist_user_count, similar_artist_user_count=similar_artist_user_count),
        recipients=['listenbrainz-observability@metabrainz.org'],
        from_name='ListenBrainz',
        from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
    )


def handle_similar_users(message):
    """ Save the similar users data to the DB
    """

    if current_app.config['TESTING']:
        return

    user_count, avg_similar_users, error = import_user_similarities(message['data'])
    if error:
        send_mail(
            subject='Similar User data failed to be calculated',
            text=render_template('emails/similar_users_failed_notification.txt', error=error),
            recipients=['listenbrainz-observability@metabrainz.org'],
            from_name='ListenBrainz',
            from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
        )
    else:
        send_mail(
            subject='Similar User data has been calculated',
            text=render_template('emails/similar_users_updated_notification.txt', user_count=str(user_count), avg_similar_users="%.1f" % avg_similar_users),
            recipients=['listenbrainz-observability@metabrainz.org'],
            from_name='ListenBrainz',
            from_addr='noreply@'+current_app.config['MAIL_FROM_DOMAIN'],
        )


def handle_similar_users_year_end(message):
    year_in_music.insert_similar_users(message["data"])


def handle_new_releases_of_top_artists(message):
    user_id = message["user_id"]
    # need to check whether user exists before inserting otherwise possible FK error.
    user = db_user.get(user_id)
    if not user:
        return
    year_in_music.insert_new_releases_of_top_artists(user_id, message["data"])


def handle_most_prominent_color(message):
    year_in_music.insert_most_prominent_color(message["data"])


def handle_day_of_week(message):
    year_in_music.insert_day_of_week(message["data"])


def handle_most_listened_year(message):
    year_in_music.insert_most_listened_year(message["data"])


def handle_top_stats(message):
    year_in_music.handle_top_stats(message["entity"], message["data"])

    # for top_releases, look up cover art
    if message["entity"] == "releases":
        data = message["data"]
        for user_data in data:
            user = db_user.get(user_data["user_id"])
            if not user:
                return
            release_mbids = [rel["release_mbid"] for rel in user_data["data"] if "release_mbid" in rel]
            coverart = year_in_music.get_coverart_for_top_releases(release_mbids)
            year_in_music.handle_coverart(user_data["user_id"], "top_releases_coverart", coverart)


def handle_listens_per_day(message):
    user_id = message["user_id"]
    user = db_user.get(user_id)
    if not user:
        return
    year_in_music.handle_listens_per_day(user_id, message["data"])


def handle_yearly_listen_counts(message):
    year_in_music.handle_yearly_listen_counts(message["data"])
