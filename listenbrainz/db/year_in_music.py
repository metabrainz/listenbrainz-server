import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
import os

import psycopg2
import sqlalchemy
import ujson
from flask import current_app, render_template
from psycopg2.extras import execute_values
from brainzutils import musicbrainz_db
from psycopg2.sql import SQL, Literal

from listenbrainz.db.model.user_timeline_event import NotificationMetadata
from listenbrainz import db
from listenbrainz.db import timescale
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
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT data FROM statistics.year_in_music WHERE user_id = :user_id AND year = :year
        """), {"user_id": user_id, "year": year})
        row = result.fetchone()
        return row["data"] if row else None


def insert(key, year, data):
    connection = db.engine.raw_connection()
    query = SQL("""
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT "user".id
                  , {year}
                  , jsonb_build_object({key}, value)
               FROM (VALUES %s) AS t(user_id, value)
               JOIN "user"
                 ON "user".id = user_id::int
        ON CONFLICT (user_id, year)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
    """).format(year=Literal(year), key=Literal(key))
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, ujson.loads(data).items())
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error(f"Error while inserting {key}:", exc_info=True)


def insert_new_releases_of_top_artists(user_id, year, data):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.year_in_music (user_id, year, data)
                 VALUES (:user_id ::int, :year, jsonb_build_object('new_releases_of_top_artists', :data :: jsonb))
            ON CONFLICT (user_id, year)
          DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """), {"user_id": user_id, "year": year, "data": ujson.dumps(data)})


def handle_multi_large_insert(key, year, data):
    connection = db.engine.raw_connection()
    query = SQL("""
        INSERT INTO statistics.year_in_music (user_id, year, data)
             SELECT "user".id
                  , {year}
                  , jsonb_build_object({key}, data::jsonb)
               FROM (VALUES %s) AS t(user_id, data)
               JOIN "user"
                 ON "user".id = user_id::int
        ON CONFLICT (user_id, year)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
    """).format(key=Literal(key), year=Literal(year))
    try:
        with connection.cursor() as cursor:
            values = [(user["user_id"], ujson.dumps(user["data"])) for user in data]
            execute_values(cursor, query, values)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting top stats:", exc_info=True)


def insert_playlists(year, playlists):
    connection = db.engine.raw_connection()
    query = SQL("""
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT user_id
                  , {year}
                  , jsonb_build_object(slug, playlist_mbid)
               FROM (VALUES %s) AS t(user_id, slug, playlist_mbid)
        ON CONFLICT (user_id, year)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
    """).format(year=Literal(year))

    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, playlists)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error(f"Error while inserting playlists:", exc_info=True)


def send_mail(subject, to_name, to_email, text, html, lb_logo, lb_logo_cid):
    if not to_email:
        return

    message = EmailMessage()
    message["From"] = f"ListenBrainz <noreply@{current_app.config['MAIL_FROM_DOMAIN']}>"
    message["To"] = f"{to_name} <{to_email}>"
    message["Subject"] = subject

    message.set_content(text)
    message.add_alternative(html, subtype="html")

    message.get_payload()[1].add_related(lb_logo, 'image', 'png', cid=lb_logo_cid, filename="listenbrainz-logo.png")
    if current_app.config["TESTING"]:  # Not sending any emails during the testing process
        return

    with smtplib.SMTP(current_app.config["SMTP_SERVER"], current_app.config["SMTP_PORT"]) as server:
        server.send_message(message)

    current_app.logger.info("Email sent to %s", to_name)


def notify_yim_users(year):
    lb_logo_cid = make_msgid()
    with open("/static/img/listenbrainz-logo.png", "rb") as img:
        lb_logo = img.read()

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id
                 , musicbrainz_id
                 , email
              FROM statistics.year_in_music yim
              JOIN "user"
                ON "user".id = yim.user_id
             WHERE year = :year   
        """), {"year": year})
        rows = result.mappings().fetchall()

    for row in rows:
        user_name = row["musicbrainz_id"]

        # cannot use url_for because we do not set SERVER_NAME and
        # a request_context will not be available in this script.
        base_url = "https://listenbrainz.org"
        year_in_music = f"{base_url}/user/{user_name}/year-in-music/"
        params = {
            "user_name": user_name,
            "year_in_music": year_in_music,
            "statistics": f"{base_url}/user/{user_name}/reports/",
            "feed": f"{base_url}/feed/",
            "feedback": f"{base_url}/user/{user_name}/feedback/",
            "pins": f"{base_url}/user/{user_name}/pins/",
            "playlists": f"{base_url}/user/{user_name}/playlists/",
            "collaborations": f"{base_url}/user/{user_name}/collaborations/",
            "lb_logo_cid": lb_logo_cid[1:-1]
        }

        try:
            send_mail(
                subject="Year In Music 2021",
                text=render_template("emails/year_in_music.txt", **params),
                to_email=row["email"],
                to_name=user_name,
                html=render_template("emails/year_in_music.html", **params),
                lb_logo_cid=lb_logo_cid,
                lb_logo=lb_logo
            )
        except Exception:
            current_app.logger.error("Could not send YIM email to %s", user_name, exc_info=True)

        # create timeline event too
        timeline_message = 'ListenBrainz\' very own retrospective on 2021 has just dropped: Check out ' \
                           f'your own <a href="{year_in_music}">Year in Music</a> now!'
        metadata = NotificationMetadata(creator="troi-bot", message=timeline_message)
        create_user_notification_event(row["user_id"], metadata)
