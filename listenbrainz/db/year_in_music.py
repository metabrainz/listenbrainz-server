import json
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
import os

import psycopg2
import sqlalchemy
import orjson
from flask import current_app, render_template
from psycopg2.extras import execute_values, DictCursor
from brainzutils import musicbrainz_db
from psycopg2.sql import SQL, Literal

from listenbrainz.db.model.user_timeline_event import NotificationMetadata
from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.db.msid_mbid_mapping import load_recordings_from_mbids
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
      DO UPDATE SET data = COALESCE(statistics.year_in_music.data, '{{}}'::jsonb) || EXCLUDED.data
    """).format(year=Literal(year), key=Literal(key))
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, orjson.loads(data).items())
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
          DO UPDATE SET data = COALESCE(statistics.year_in_music.data, '{}'::jsonb) || EXCLUDED.data
        """), {"user_id": user_id, "year": year, "data": orjson.dumps(data).decode("utf-8")})


def insert_similar_recordings(year, data):
    connection = db.engine.raw_connection()
    query = SQL("""
        INSERT INTO statistics.year_in_music (user_id, year, data)
             SELECT "user".id
                  , {year}
                  , jsonb_build_object('similar_users', jsonb_object_agg(other_user.musicbrainz_id, similar_user.score::float))
               FROM (VALUES %s) AS t(user_id, data)
               JOIN "user"
                 ON "user".id = user_id::int
       JOIN LATERAL jsonb_each(t.data::jsonb) AS similar_user(user_id, score)
                 ON TRUE
               JOIN "user" other_user
                 ON other_user.id = similar_user.user_id::int
           GROUP BY "user".id
        ON CONFLICT (user_id, year)
      DO UPDATE SET data = COALESCE(statistics.year_in_music.data, '{{}}'::jsonb) || EXCLUDED.data
    """).format(year=Literal(year))
    try:
        with connection.cursor() as cursor:
            values = [(k, json.dumps(v, ensure_ascii=False)) for k, v in data.items()]
            execute_values(cursor, query, values)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting similar users:", exc_info=True)


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
      DO UPDATE SET data = COALESCE(statistics.year_in_music.data, '{{}}'::jsonb) || EXCLUDED.data
    """).format(key=Literal(key), year=Literal(year))
    try:
        with connection.cursor() as cursor:
            values = [(user["user_id"], orjson.dumps(user["data"]).decode("utf-8")) for user in data]
            execute_values(cursor, query, values)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting top stats:", exc_info=True)


def handle_insert_top_stats(entity, year, data):
    connection = db.engine.raw_connection()
    query = SQL("""
        INSERT INTO statistics.year_in_music (user_id, year, data)
             SELECT "user".id
                  , {year}
                  , jsonb_build_object({key}, data::jsonb, {count_key}, count)
               FROM (VALUES %s) AS t(user_id, count, data)
               JOIN "user"
                 ON "user".id = user_id::int
        ON CONFLICT (user_id, year)
      DO UPDATE SET data = COALESCE(statistics.year_in_music.data, '{{}}'::jsonb) || EXCLUDED.data
    """).format(key=Literal(f"top_{entity}"), count_key=Literal(f"total_{entity}_count"), year=Literal(year))
    try:
        with connection.cursor() as cursor:
            values = [(user["user_id"], user["count"], orjson.dumps(user["data"]).decode("utf-8")) for user in data]
            execute_values(cursor, query, values)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting top stats:", exc_info=True)


def insert_playlists_cover_art(year, data):
    """ Insert cover art for YIM playlists. This is used to lookup cover art for the first 5 tracks of each playlist
     preview and for the SVG cover on YIM page. """
    all_mbids = set()
    for (user_id, slug, playlist) in data:
        for track in playlist["track"]:
            mbid = track["identifier"].split("/")[-1]
            all_mbids.add(mbid)

    with timescale.engine.connect() as ts_conn, ts_conn.connection.cursor(cursor_factory=DictCursor) as ts_cursor:
        recordings = load_recordings_from_mbids(ts_cursor, all_mbids)

    cover_art_data = []
    for (user_id, slug, playlist) in data:
        cover_arts = {}
        for track in playlist["track"]:
            mbid = track["identifier"].split("/")[-1]
            r = recordings.get(mbid)
            if r:
                caa_release_mbid = r["caa_release_mbid"]
                caa_id = r["caa_id"]
                if caa_id and caa_release_mbid:
                    url = f"https://archive.org/download/mbid-{caa_release_mbid}/mbid-{caa_release_mbid}-{caa_id}_thumb500.jpg"
                    cover_arts[mbid] = url

        cover_art_data.append((user_id, f"{slug}-coverart", cover_arts))

    insert_playlists(year, cover_art_data)


def insert_playlists(year, data):
    """ Insert playlists data for the year in music """
    connection = db.engine.raw_connection()
    query = SQL("""
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT user_id
                  , {year}
                  , jsonb_object_agg(slug, playlist::jsonb)
               FROM (VALUES %s) AS t(user_id, slug, playlist)
           GROUP BY user_id
        ON CONFLICT (user_id, year)
      DO UPDATE SET data = COALESCE(statistics.year_in_music.data, '{{}}'::jsonb) || EXCLUDED.data
    """).format(year=Literal(year))

    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, [(user, slug, orjson.dumps(playlist).decode("utf-8")) for user, slug, playlist in data])
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error(f"Error while inserting playlists:", exc_info=True)


def create_tracks_of_the_year(year):
    connection = timescale.engine.raw_connection()
    query = SQL("""
        CREATE TABLE IF NOT EXISTS mapping.tracks_of_the_year_{year} (
            user_id             INTEGER     NOT NULL,
            recording_mbid      UUID        NOT NULL,
            recording_name      TEXT        NOT NULL,
            artist_name         TEXT        NOT NULL,
            artist_credit_mbids TEXT[],
            listen_count        INTEGER     NOT NULL
        )
    """).format(year=Literal(year))
    truncate_query = SQL("TRUNCATE TABLE mapping.tracks_of_the_year_{year}").format(year=Literal(year))
    drop_query = SQL("DROP INDEX IF EXISTS tracks_of_the_year_{year}_user_id_idx").format(year=Literal(year))
    with connection.cursor() as curs:
        curs.execute(query)
        curs.execute(truncate_query)
        curs.execute(drop_query)
    connection.commit()


def finalise_tracks_of_the_year(year):
    connection = timescale.engine.raw_connection()
    query = SQL("""
        CREATE INDEX IF NOT EXISTS tracks_of_the_year_{year}_user_id_idx ON mapping.tracks_of_the_year_{year} (user_id)
    """).format(year=Literal(year))
    with connection.cursor() as curs:
        curs.execute(query)
    connection.commit()


def insert_tracks_of_the_year(year, data):
    query = SQL("""
        INSERT INTO mapping.tracks_of_the_year_{year} (user_id, recording_name, recording_mbid, artist_name, artist_credit_mbids, listen_count) VALUES %s
    """).format(year=Literal(year))
    connection = timescale.engine.raw_connection()
    with connection.cursor() as curs:
        values = [(r["user_id"], r["recording_name"], r["recording_mbid"], r["artist_name"], r["artist_credit_mbids"], r["listen_count"]) for r in data]
        execute_values(curs, query, values, page_size=5000)
    connection.commit()


def send_mail(subject, to_name, to_email, text, html, logo, logo_cid):
    if not to_email:
        return

    message = EmailMessage()
    message["From"] = f"ListenBrainz <noreply@{current_app.config['MAIL_FROM_DOMAIN']}>"
    message["To"] = f"{to_name} <{to_email}>"
    message["Subject"] = subject

    message.set_content(text)
    message.add_alternative(html, subtype="html")

    message.get_payload()[1].add_related(logo, 'image', 'png', cid=logo_cid, filename="year-in-music-2022-logo.png")
    if current_app.config["TESTING"]:  # Not sending any emails during the testing process
        return

    with smtplib.SMTP(current_app.config["SMTP_SERVER"], current_app.config["SMTP_PORT"]) as server:
        server.send_message(message)

    current_app.logger.info("Email sent to %s", to_name)


def notify_yim_users(year):
    logo_cid = make_msgid()
    with open("/static/img/year-in-music-22/yim-22-logo-small-compressed.png", "rb") as img:
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
