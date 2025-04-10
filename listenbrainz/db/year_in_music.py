import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

import psycopg2
import sqlalchemy
import orjson
from flask import current_app, render_template
from psycopg2.extras import execute_values
from psycopg2.sql import SQL, Literal, Identifier
from sqlalchemy import text

from listenbrainz.db.model.user_timeline_event import NotificationMetadata
from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.db.user import get_all_usernames
from listenbrainz.db.user_timeline_event import create_user_notification_event

# Year in Music data element defintions
#
# The following keys are being used to populate the data JSONB element of the year_in_music table:
#
# day_of_week
# listens_per_day
# most_listened_year
# most_prominent_color
# new_releases_of_top_artists
# playlist-top-discoveries-for-year-playlists
# playlist-top-missed-recordings-for-year-playlists
# playlist-top-new-recordings-for-year-playlists
# playlist-top-recordings-for-year-playlists
# similar_users
# top_artists
# top_recordings
# top_releases
# top_releases_coverart
# total_listen_count


def get(user_id, year):
    """ Get year in music data for requested user """
    if year not in [2021, 2022, 2023, 2024]:
        return None

    table = "statistics.year_in_music_" + str(year)
    with timescale.engine.connect() as connection:
        result = connection.execute(
            text("SELECT data FROM " + table + " WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        row = result.fetchone()
        return row.data if row else None


def insert(key, year, data, cast_to_jsonb):
    table = "year_in_music_" + str(year) + "_tmp"
    connection = timescale.engine.raw_connection()
    query = SQL("""
        INSERT INTO {table} AS yim
                    (VALUES %s)
        ON CONFLICT (user_id)
      DO UPDATE SET data = COALESCE(yim.data, '{{}}'::jsonb) || EXCLUDED.data
    """).format(table=Identifier("statistics", table), key=Literal(key))
    if cast_to_jsonb:
        template = f"(%s, jsonb_build_object('{key}', %s::jsonb))"
    else:
        template = f"(%s, jsonb_build_object('{key}', %s))"
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, data, template)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error(f"Error while inserting {key}:", exc_info=True)


def insert_light(key, year, data):
    table = "year_in_music_" + str(year) + "_tmp"
    connection = timescale.engine.raw_connection()
    query = SQL("""
        INSERT INTO {table} AS yim
             SELECT user_id::int
                  , jsonb_build_object({key}, value) AS data
               FROM jsonb_each(%s::jsonb) AS t(user_id, value)
        ON CONFLICT (user_id)
      DO UPDATE SET data = COALESCE(yim.data, '{{}}'::jsonb) || EXCLUDED.data
    """).format(table=Identifier("statistics", table), key=Literal(key))
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (data,))
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error(f"Error while inserting {key}:", exc_info=True)


def insert_heavy(key, year, data):
    insert(key, year, [(user["user_id"], orjson.dumps(user["data"]).decode("utf-8")) for user in data], True)


def insert_similar_users(year, data):
    user_ids = get_all_usernames()

    similar_user_data = [
        {
            "user_id": int(user_id),
            "data": {
                user_ids[int(other_user_id)]: score
                for other_user_id, score in similar_users.items()
                if int(other_user_id) in user_ids
            }
        }
        for user_id, similar_users in data.items()
    ]

    insert_heavy("similar_users", year, similar_user_data)


def insert_top_stats(entity, year, data):
    insert_heavy(f"top_{entity}", year, data)
    insert(f"total_{entity}_count", year, [(user["user_id"], user["count"]) for user in data], False)


def create_yim_table(year):
    """ Create a new year in music unlogged table for the specified year """
    table = "statistics.year_in_music_" + str(year) + "_tmp"
    drop_sql = "DROP TABLE IF EXISTS " + table
    create_sql = """
        CREATE UNLOGGED TABLE """ + table + """ (
            user_id INTEGER NOT NULL PRIMARY KEY,
            data JSONB NOT NULL
        )
    """
    with timescale.engine.begin() as connection:
        connection.execute(text(drop_sql))
        connection.execute(text(create_sql))


def swap_yim_tables(year):
    """ Swap the year in music tables """
    table_without_schema = "year_in_music_" + str(year)
    table = "statistics." + table_without_schema
    tmp_table = table + "_tmp"

    drop_sql = "DROP TABLE IF EXISTS " + table
    rename_sql = "ALTER TABLE IF EXISTS " + tmp_table + " RENAME TO " + table_without_schema
    logged_sql = "ALTER TABLE IF EXISTS " + table + " SET LOGGED"
    vacuum_sql = "VACUUM ANALYZE " + tmp_table
    with timescale.engine.connect() as connection:
        connection.connection.set_isolation_level(0)
        connection.execute(text(vacuum_sql))

    with timescale.engine.begin() as connection:
        connection.execute(text(drop_sql))
        connection.execute(text(rename_sql))
        connection.execute(text(logged_sql))


def send_mail(subject, to_name, to_email, content, html, logo, logo_cid):
    if not to_email:
        return

    message = EmailMessage()
    message["From"] = f"ListenBrainz <noreply@{current_app.config['MAIL_FROM_DOMAIN']}>"
    message["To"] = f"{to_name} <{to_email}>"
    message["Subject"] = subject

    message.set_content(content)
    message.add_alternative(html, subtype="html")

    message.get_payload()[1].add_related(logo, 'image', 'png', cid=logo_cid, filename="year-in-music-23-logo.png")
    if current_app.config["TESTING"]:  # Not sending any emails during the testing process
        return

    with smtplib.SMTP(current_app.config["SMTP_SERVER"], current_app.config["SMTP_PORT"]) as server:
        server.send_message(message)

    current_app.logger.info("Email sent to %s", to_name)


def sanitize_username(username):
    username.replace('\\','\\\\')
    username.replace('"','\\"')
    return f'"{username}"'


def notify_yim_users(db_conn, ts_conn, year):
    logo_cid = make_msgid()
    with open("/static/img/year-in-music-24/yim24-header-all-email.png", "rb") as img:
        logo = img.read()

    if year not in [2021, 2022, 2023, 2024]:
        return None

    table = "statistics.year_in_music_" + str(year)

    result = ts_conn.execute(text("SELECT user_id FROM " + table + " WHERE data IS NOT NULL"))
    user_ids = [row.user_id for row in result.fetchall()]

    result = db_conn.execute(
        text('SELECT id AS user_id, email, musicbrainz_id FROM "user" WHERE id = ANY(:user_ids)'),
        {"user_ids": user_ids}
    )
    rows = result.fetchall()

    for row in rows:
        user_name = sanitize_username(row.musicbrainz_id)

        # cannot use url_for because we do not set SERVER_NAME and
        # a request_context will not be available in this script.
        base_url = "https://listenbrainz.org"
        year_in_music = f"{base_url}/user/{user_name}/year-in-music/{year}/"
        params = {
            "user_name": user_name,
            "logo_cid": logo_cid[1:-1]
        }

        try:
            send_mail(
                subject=f"Year In Music {year}",
                content=render_template("emails/year_in_music.txt", **params),
                to_email=row.email,
                to_name=user_name,
                html=render_template("emails/year_in_music.html", **params),
                logo_cid=logo_cid,
                logo=logo
            )
        except Exception:
            current_app.logger.error("Could not send YIM email to %s", user_name, exc_info=True)

        # create timeline event too
        timeline_message = f'ListenBrainz\' very own retrospective on {year} has just dropped: Check out ' \
                           f'your own <a href="{year_in_music}">Year in Music</a> now!'
        metadata = NotificationMetadata(creator="troi-bot", message=timeline_message)
        create_user_notification_event(db_conn, row.user_id, metadata)
