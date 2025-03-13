""" This file contains handler functions for rabbitmq messages we
    receive from the Spark cluster.
"""
import json

from brainzutils.mail import send_mail
from flask import current_app, render_template
from pydantic import ValidationError
from requests import HTTPError
from sentry_sdk import start_transaction

import listenbrainz.db.missing_musicbrainz_data as db_missing_musicbrainz_data
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from data.model.user_cf_recommendations_recording_message import UserRecommendationsJson
from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataJson
from listenbrainz.db import year_in_music, couchdb
from listenbrainz.db.fresh_releases import insert_fresh_releases
from listenbrainz.db import similarity
from listenbrainz.db.similar_users import import_user_similarities
from listenbrainz.troi.daily_jams import run_post_recommendation_troi_bot
from listenbrainz.troi.weekly_playlists import process_weekly_playlists, process_weekly_playlists_end
from listenbrainz.troi.year_in_music import process_yim_playlists, process_yim_playlists_end
from listenbrainz.webserver import db_conn

TIME_TO_CONSIDER_STATS_AS_OLD = 20  # minutes
TIME_TO_CONSIDER_RECOMMENDATIONS_AS_OLD = 7  # days


def _handle_stats(message, stats_type, key):
    try:
        with start_transaction(op="insert", name=f'insert {stats_type} - {message["stats_range"]} stats'):
            db_stats.insert(
                message["database"],
                message["from_ts"],
                message["to_ts"],
                message["data"],
                key
            )
    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


def handle_user_entity(message):
    """ Take entity stats for a user and save it in the database. """
    _handle_stats(message, f'user {message["entity"]}', "user_id")


def handle_entity_listener(message):
    """ Take listener stats for an entity and save it in the database """
    if message["entity"] == "artists":
        key = "artist_mbid"
    elif message["entity"] == "releases":
        key = "release_mbid"
    elif message["entity"] == "release_groups":
        key = "release_group_mbid"
    else:
        key = "recording_mbid"
    _handle_stats(message, f'{message["entity"]} listeners', key)


def handle_user_listening_activity(message):
    """ Take listening activity stats for user and save it in database. """
    _handle_stats(message, "listening_activity", "user_id")


def handle_user_daily_activity(message):
    """ Take daily activity stats for user and save it in database. """
    _handle_stats(message, "daily_activity", "user_id")


def _handle_sitewide_stats(message, stat_type, has_count=False):
    try:
        stats = {
            "data": message["data"]
        }
        if has_count:
            stats["count"] = message["count"]

        db_stats.insert_sitewide_stats(
            stat_type,
            message["stats_range"],
            message["from_ts"],
            message["to_ts"],
            stats
        )
    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


def handle_sitewide_entity(message):
    """ Take sitewide entity stats and save it in the database. """
    _handle_sitewide_stats(message, message["entity"], has_count=True)


def handle_sitewide_artist_map(message):
    _handle_sitewide_stats(message, "artist_map")


def handle_sitewide_listening_activity(message):
    _handle_sitewide_stats(message, "listening_activity")


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
    user = db_user.get(db_conn, user_id)

    if not user:
        return

    current_app.logger.debug(f"Inserting missing musicbrainz data for {user['musicbrainz_id']}")

    missing_musicbrainz_data = data['missing_musicbrainz_data']
    source = data['source']

    try:
        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            db_conn,
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
    user = db_user.get(db_conn, user_id)
    if not user:
        current_app.logger.info(f"Generated recommendations for a user that doesn't exist in the Postgres database: {user_id}")
        return

    current_app.logger.debug("inserting recommendation for {}".format(user["musicbrainz_id"]))
    recommendations = data['recommendations']

    try:
        db_recommendations_cf_recording.insert_user_recommendation(
            db_conn,
            user_id,
            UserRecommendationsJson(**recommendations)
        )
    except ValidationError:
        current_app.logger.error(f"""ValidationError while inserting recommendations for user with musicbrainz_id:
                                 {user["musicbrainz_id"]}. \nData: {json.dumps(data, indent=3)}""")

    current_app.logger.debug("recommendation for {} inserted".format(user["musicbrainz_id"]))

    current_app.logger.debug("Running post recommendation steps for user {}".format(user["musicbrainz_id"]))


def handle_fresh_releases(message):
    try:
        insert_fresh_releases(message["database"], message["data"])
    except HTTPError as e:
        current_app.logger.error(f"{str(e)}. Response: %s", e.response.json(), exc_info=True)


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


def cf_recording_recommendations_complete(data):
    """
    Run any troi scripts necessary now that recommendations have been generated and
    send an email to notify recommendations have been generated and are being written into db.
    """
    run_post_recommendation_troi_bot()

    if current_app.config['TESTING']:
        return

    active_user_count = data['active_user_count']
    total_time = data['total_time']
    send_mail(
        subject='Recommendations have been generated and pushed to the queue.',
        text=render_template('emails/cf_recording_recommendation_notification.txt',
                             active_user_count=active_user_count, total_time=total_time),
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


def handle_yim_similar_users(message):
    year_in_music.insert_similar_users(message["year"], message["data"])


def handle_yim_new_releases_of_top_artists(message):
    year_in_music.insert_heavy("new_releases_of_top_artists", message["year"], message["data"])


def handle_yim_day_of_week(message):
    year_in_music.insert_light("day_of_week", message["year"], message["data"])


def handle_yim_most_listened_year(message):
    year_in_music.insert_heavy("most_listened_year", message["year"], message["data"])


def handle_yim_top_stats(message):
    year_in_music.insert_top_stats(message["entity"], message["year"], message["data"])


def handle_yim_listens_per_day(message):
    year_in_music.insert_heavy("listens_per_day", message["year"], message["data"])


def handle_yim_listen_counts(message):
    year_in_music.insert_light("total_listen_count", message["year"], message["data"])


def handle_yim_listening_time(message):
    year_in_music.insert_light("total_listening_time", message["year"], message["data"])


def handle_yim_artist_map(message):
    year_in_music.insert_heavy("artist_map", message["year"], message["data"])


def handle_yim_new_artists_discovered_count(message):
    year_in_music.insert_light("total_new_artists_discovered", message["year"], message["data"])


def handle_yim_top_genres(message):
    year_in_music.insert_heavy("top_genres", message["year"], message["data"])


def handle_yim_playlists(message):
    process_yim_playlists(message["slug"], message["year"], message["data"])


def handle_yim_playlists_end(message):
    process_yim_playlists_end(message["slug"], message["year"])


def handle_similar_recordings(message):
    similarity.insert("recording", message["data"], message["algorithm"])


def handle_similar_artists(message):
    similarity.insert("artist_credit_mbids", message["data"], message["algorithm"])


def handle_troi_playlists(message):
    process_weekly_playlists(message["slug"], message["data"])


def handle_troi_playlists_end(message):
    process_weekly_playlists_end(message["slug"])


def handle_echo(message):
    if message["message"]["action"] == "year_in_music_start":
        year_in_music.create_yim_table(message["message"]["year"])
    elif message["message"]["action"] == "year_in_music_end":
        year_in_music.swap_yim_tables(message["message"]["year"])
    else:
        current_app.logger.info("message with unknown action: %s", json.dumps(message))
