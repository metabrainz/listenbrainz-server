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
    if year not in [2021, 2022, 2023]:
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
    connection = timescale.engine.raw_connection()
    query = SQL("""
        INSERT INTO {table} AS yim (user_id, data)
             SELECT user_id
                  , jsonb_build_object({key}, value::jsonb)
               FROM (VALUES %s) AS t(user_id, value)
        ON CONFLICT (user_id)
      DO UPDATE SET data = COALESCE(yim.data, '{{}}'::jsonb) || EXCLUDED.data
    """).format(table=Identifier("statistics", "year_in_music_" + year), key=Literal(key))
    if cast_to_jsonb:
        template = f"jsonb_build_object('{key}', value::jsonb)"
    else:
        template = f"jsonb_build_object('{key}', value)"
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, data, template)
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
            "user_id": user["user_id"],
            "data": orjson.dumps(
                [
                    {
                        "musicbrainz_id": user_ids[other_user["user_id"]],
                        "score": other_user["score"]
                    }
                    for other_user in user["data"]
                    if other_user["user_id"] in user_ids
                ]
            ).decode("utf-8")
        }
        for user in data
    ]

    insert_heavy("similar_users", year, similar_user_data)


def insert_top_stats(entity, year, data):
    insert_heavy(f"top_{entity}", year, data)
    insert(f"total_{entity}_count", year, [(user["user_id"], user["count"]) for user in data], False)



def send_mail(subject, to_name, to_email, text, html, logo, logo_cid):
    if not to_email:
        return

    message = EmailMessage()
    message["From"] = f"ListenBrainz <noreply@{current_app.config['MAIL_FROM_DOMAIN']}>"
    message["To"] = f"{to_name} <{to_email}>"
    message["Subject"] = subject

    message.set_content(text)
    message.add_alternative(html, subtype="html")

    message.get_payload()[1].add_related(logo, 'image', 'png', cid=logo_cid, filename="year-in-music-23-logo.png")
    if current_app.config["TESTING"]:  # Not sending any emails during the testing process
        return

    with smtplib.SMTP(current_app.config["SMTP_SERVER"], current_app.config["SMTP_PORT"]) as server:
        server.send_message(message)

    current_app.logger.info("Email sent to %s", to_name)


def notify_yim_users(year):
    logo_cid = make_msgid()
    with open("/static/img/year-in-music-23/yim-23-logo-small-compressed.png", "rb") as img:
        logo = img.read()

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id
                 , musicbrainz_id
                 , email
              FROM statistics.year_in_music yim
              JOIN "user"
                ON "user".id = yim.user_id
             WHERE year = :year
               AND data IS NOT NULL
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
            "logo_cid": logo_cid[1:-1]
        }

        try:
            send_mail(
                subject=f"Year In Music {year}",
                text=render_template("emails/year_in_music.txt", **params),
                to_email=row["email"],
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
        create_user_notification_event(row["user_id"], metadata)
