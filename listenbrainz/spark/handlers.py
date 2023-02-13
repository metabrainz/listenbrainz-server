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
from listenbrainz.troi.troi_bot import run_post_recommendation_troi_bot
from listenbrainz.troi.year_in_music import yim_patch_runner

TIME_TO_CONSIDER_STATS_AS_OLD = 20  # minutes
TIME_TO_CONSIDER_RECOMMENDATIONS_AS_OLD = 7  # days


def handle_couchdb_data_start(message):
    match = couchdb.DATABASE_NAME_PATTERN.match(message["database"])
    if not match:
        return
    try:
        couchdb.create_database(match[1] + "_" + match[2] + "_" + match[3])
        if match[1] == "artists":
            couchdb.create_database("artistmap" + "_" + match[2] + "_" + match[3])
    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


def handle_couchdb_data_end(message):
    # database names are of the format, prefix_YYYYMMDD. calculate and pass the prefix to the
    # method to delete all database of the type except the latest one.
    match = couchdb.DATABASE_NAME_PATTERN.match(message["database"])
    # if the database name does not match pattern, abort to avoid deleting any data inadvertently
    if not match:
        return
    try:
        _, retained = couchdb.delete_database(match[1] + "_" + match[2])
        if retained:
            current_app.logger.info(f"Databases: {retained} matched but weren't deleted because"
                                    f" _LOCK file existed")

        # when new artist stats received, also invalidate old artist map stats
        if match[1] == "artists":
            _, retained = couchdb.delete_database("artistmap" + "_" + match[2])
            if retained:
                current_app.logger.info(f"Databases: {retained} matched but weren't deleted because"
                                        f" _LOCK file existed")

    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


def _handle_stats(message, stats_type):
    try:
        with start_transaction(op="insert", name=f'insert {stats_type} - {message["stats_range"]} stats'):
            db_stats.insert(
                message["database"],
                message["from_ts"],
                message["to_ts"],
                message["data"]
            )
    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


def handle_user_entity(message):
    """ Take entity stats for a user and save it in the database. """
    _handle_stats(message, message["entity"])


def handle_user_listening_activity(message):
    """ Take listening activity stats for user and save it in database. """
    _handle_stats(message, "listening_activity")


def handle_user_daily_activity(message):
    """ Take daily activity stats for user and save it in database. """
    _handle_stats(message, "daily_activity")


def _handle_sitewide_stats(message, stat_type, has_count=False):
    try:
        stats_range = message["stats_range"]
        databases = couchdb.list_databases(f"{stat_type}_{stats_range}")
        if not databases:
            current_app.logger.error(f"No database found to insert {stats_range} sitewide {stat_type} stats")
            return

        stats = {
            "data": message["data"]
        }
        if has_count:
            stats["count"] = message["count"]

        db_stats.insert_sitewide_stats(
            databases[0],
            message["from_ts"],
            message["to_ts"],
            stats
        )
    except HTTPError as e:
        current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)


def handle_sitewide_entity(message):
    """ Take sitewide entity stats and save it in the database. """
    _handle_sitewide_stats(message, message["entity"], has_count=True)


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


def handle_yim_similar_users(message):
    year_in_music.insert_similar_recordings(message["year"], message["data"])


def handle_yim_new_releases_of_top_artists(message):
    user_id = message["user_id"]
    # need to check whether user exists before inserting otherwise possible FK error.
    user = db_user.get(user_id)
    if not user:
        return
    year_in_music.insert_new_releases_of_top_artists(user_id, message["year"], message["data"])


def handle_yim_day_of_week(message):
    year_in_music.insert("day_of_week", message["year"], message["data"])


def handle_yim_most_listened_year(message):
    year_in_music.handle_multi_large_insert("most_listened_year", message["year"], message["data"])


def handle_yim_top_stats(message):
    year_in_music.handle_insert_top_stats(message["entity"], message["year"], message["data"])


def handle_yim_listens_per_day(message):
    year_in_music.handle_multi_large_insert("listens_per_day", message["year"], message["data"])


def handle_yim_listen_counts(message):
    year_in_music.insert("total_listen_count", message["year"], message["data"])


def handle_yim_listening_time(message):
    year_in_music.insert("total_listening_time", message["year"], message["data"])


def handle_yim_artist_map(message):
    year_in_music.handle_multi_large_insert("artist_map", message["year"], message["data"])


def handle_new_artists_discovered_count(message):
    year_in_music.insert("total_new_artists_discovered", message["year"], message["data"])


def handle_yim_tracks_of_the_year_start(message):
    year_in_music.create_tracks_of_the_year(message["year"])


def handle_yim_tracks_of_the_year_data(message):
    year_in_music.insert_tracks_of_the_year(message["year"], message["data"])


def handle_yim_tracks_of_the_year_end(message):
    # all of the tracks data has been inserted, now we can generate the playlists
    year_in_music.finalise_tracks_of_the_year(message["year"])
    yim_patch_runner(message["year"])


def handle_similar_recordings(message):
    similarity.insert("recording", message["data"], message["algorithm"])


def handle_similar_artists(message):
    similarity.insert("artist_credit_mbids", message["data"], message["algorithm"])
