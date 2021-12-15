import smtplib
from email.message import EmailMessage

import psycopg2
import sqlalchemy
import ujson
from flask import current_app, render_template
from psycopg2.extras import execute_values

from data.model.user_timeline_event import NotificationMetadata
from listenbrainz import db
from listenbrainz.db.user_timeline_event import create_user_notification_event



def get_year_in_music(user_id):
    """ Get year in music data for requested user """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT data FROM statistics.year_in_music WHERE user_id = :user_id
        """), user_id=user_id)
        row = result.fetchone()
        return row["data"] if row else None


def insert_new_releases_of_top_artists(user_id, data):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.year_in_music (user_id, data)
                 VALUES (:user_id, jsonb_build_object('new_releases_of_top_artists', :data :: jsonb))
            ON CONFLICT (user_id)
          DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """), user_id=user_id, data=ujson.dumps(data))


def insert_most_prominent_color(data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, data)
             SELECT "user".id
                  , jsonb_build_object('most_prominent_color', color)
               FROM (VALUES %s) AS t(user_name, color)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_colors = ujson.loads(data)
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, user_colors.items())
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting most prominent colors:", exc_info=True)


def insert_similar_users(data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, data)
             SELECT "user".id
                  , jsonb_build_object('similar_users', similar_users::jsonb)
               FROM (VALUES %s) AS t(user_name, similar_users)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    similar_users = [(k, ujson.dumps(v)) for k, v in data.items()]
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, similar_users)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting similar users:", exc_info=True)


def insert_day_of_week(data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, data)
             SELECT "user".id
                  , jsonb_build_object('day_of_week', weekday)
               FROM (VALUES %s) AS t(user_name, weekday)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_weekdays = ujson.loads(data)
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, user_weekdays.items())
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting day of week:", exc_info=True)


def insert_most_listened_year(data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, data)
             SELECT "user".id
                  , jsonb_build_object('most_listened_year', yearly_counts::jsonb)
               FROM (VALUES %s) AS t(user_name, yearly_counts)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_listened_years = [(k, ujson.dumps(v)) for k, v in ujson.loads(data).items()]
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, user_listened_years)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting most_listened_year:", exc_info=True)


def handle_top_stats(user_id, entity, data):
    with db.engine.connect() as connection:
        connection.execute(
            sqlalchemy.text("""
            INSERT INTO statistics.year_in_music (user_id, data)
                 VALUES (:user_id, jsonb_build_object(:stat_type,:data :: jsonb))
            ON CONFLICT (user_id)
          DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
            """),
            user_id=user_id,
            stat_type=f"top_{entity}",
            data=ujson.dumps(data)
        )


def handle_listens_per_day(user_id, data):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.year_in_music (user_id, data)
                 VALUES (:user_id, jsonb_build_object('listens_per_day', :data :: jsonb))
            ON CONFLICT (user_id)
          DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """), user_id=user_id, data=ujson.dumps(data))


def handle_yearly_listen_counts(data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, data)
             SELECT "user".id
                  , jsonb_build_object('total_listen_count', listen_count)
               FROM (VALUES %s) AS t(user_name, listen_count)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_listen_counts = ujson.loads(data)
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, user_listen_counts.items())
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting most prominent colors:", exc_info=True)


def insert_playlists(troi_patch_slug, import_file):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, data)
             SELECT "user".id
                  , playlists::jsonb
               FROM (VALUES %s) AS t(user_name, playlists)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """

    data = []
    with open(import_file, "r") as f:
        while True:
            user_name = f.readline()
            if user_name == "":
                break

            user_name = user_name.strip()
            playlist_mbid = f.readline().strip()
            jspf = f.readline().strip()

            data.append((user_name, ujson.dumps({
                f"playlist-{troi_patch_slug}": {
                    "mbid": playlist_mbid,
                    "jspf": ujson.loads(jspf)
                }
            })))

    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, data)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting playlist/%s:" % troi_patch_slug, exc_info=True)


def send_mail(subject, to_name, to_email, text, html):
    message = EmailMessage()
    message["From"] = f"ListenBrainz <noreply@{current_app.config['MAIL_FROM_DOMAIN']}>"
    message["To"] = f"{to_name} <{to_email}>"
    message["Subject"] = subject

    message.set_content(text)
    message.add_alternative(html, subtype="html")

    if current_app.config["TESTING"]:  # Not sending any emails during the testing process
        return

    with smtplib.SMTP(current_app.config["SMTP_SERVER"], current_app.config["SMTP_PORT"]) as server:
        server.send_message(message)


def notify_yim_users():
    # with db.engine.connect() as connection:
    #     result = connection.execute("""
    #         SELECT user_id
    #              , musicbrainz_id
    #              , email
    #           FROM statistics.year_in_music yim
    #           JOIN "user"
    #             ON "user".id = yim.user_id
    #     """)
    #     rows = result.fetchall()

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id AS user_id
                 , musicbrainz_id
                 , email
              FROM "user"
             WHERE musicbrainz_id IN ('amCap1712', 'rob', 'alastairp', 'mr_monkey', 'akshaaatt')    
        """))
        rows = result.fetchall()

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
            "collaborations": f"{base_url}/user/{user_name}/collaborations/"
        }

        send_mail(
            subject="Year In Music 2021",
            text=render_template("emails/year_in_music.txt", **params),
            to_email=row["email"],
            to_name=user_name,
            html=render_template("emails/year_in_music.html", **params)
        )
        # create timeline event too
        timeline_message = 'ListenBrainz\' very own retrospective on 2021 has just dropped: Check out ' \
                           f'your own <a href="{year_in_music}">Year in Music</a> now!'
        metadata = NotificationMetadata(creator="troi-bot", message=timeline_message)
        create_user_notification_event(row["user_id"], metadata)
