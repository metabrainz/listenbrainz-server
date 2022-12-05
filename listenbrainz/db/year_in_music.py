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


def get_year_in_music(user_id, year):
    """ Get year in music data for requested user """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT data FROM statistics.year_in_music WHERE user_id = :user_id AND year = :year
        """), {"user_id": user_id, "year": year})
        row = result.fetchone()
        return row["data"] if row else None


def insert_new_releases_of_top_artists(user_id, year, data):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.year_in_music (user_id, year, data)
                 VALUES (:user_id, :year, jsonb_build_object('new_releases_of_top_artists', :data :: jsonb))
            ON CONFLICT (user_id, year)
          DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """), {"user_id": user_id, "year": year, "data": ujson.dumps(data)})


def insert_most_prominent_color(year, data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT "user".id
                  , year
                  , jsonb_build_object('most_prominent_color', color)
               FROM (VALUES %s) AS t(user_id, year, color)
               JOIN "user"
                 ON "user".id = user_id
        ON CONFLICT (user_id, year)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_colors = ujson.loads(data)
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, [(k, year, v) for k, v in user_colors.items()])
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting most prominent colors:", exc_info=True)


def insert_similar_users(year, data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT "user".id
                  , jsonb_build_object('similar_users', similar_users::jsonb)
               FROM (VALUES %s) AS t(user_id, year, similar_users)
               JOIN "user"
                 ON "user".id = user_id
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    similar_users = [(k, year, ujson.dumps(v)) for k, v in data.items()]
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, similar_users)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting similar users:", exc_info=True)


def insert_day_of_week(year, data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT "user".id
                  , jsonb_build_object('day_of_week', weekday)
               FROM (VALUES %s) AS t(user_id, year, weekday)
               JOIN "user"
                 ON "user".id = user_id
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_weekdays = ujson.loads(data)
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, [(k, year, v) for k, v in user_weekdays.items()])
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting day of week:", exc_info=True)


def insert_most_listened_year(year, data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT "user".id
                  , jsonb_build_object('most_listened_year', yearly_counts::jsonb)
               FROM (VALUES %s) AS t(user_id, year, yearly_counts)
               JOIN "user"
                 ON "user".id = user_id
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_listened_years = [(k, year, ujson.dumps(v)) for k, v in ujson.loads(data).items()]
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, user_listened_years)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting most_listened_year:", exc_info=True)


def handle_top_stats(entity, year, data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music (user_id, year, data)
             SELECT "user".id
                  , jsonb_build_object(%s, top_stats::jsonb)
               FROM (VALUES %%s) AS t(user_name, year, top_stats)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
    """
    try:
        with connection.cursor() as cursor:
            query = cursor.mogrify(query, (f"top_{entity}",))
            values = [(user["musicbrainz_id"], year, ujson.dumps(user["data"])) for user in data]
            execute_values(cursor, query, values)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting top stats:", exc_info=True)


def handle_listens_per_day(user_id, year, data):
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO statistics.year_in_music (user_id, year, data)
                 VALUES (:user_id, :year, jsonb_build_object('listens_per_day', :data :: jsonb))
            ON CONFLICT (user_id, year)
          DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """), {"user_id": user_id, "year": year, "data": ujson.dumps(data)})


def handle_yearly_listen_counts(year, data):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT "user".id
                  , jsonb_build_object('total_listen_count', listen_count)
               FROM (VALUES %s) AS t(user_id, year, listen_count)
               JOIN "user"
                 ON "user".id = user_id
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """
    user_listen_counts = ujson.loads(data)
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, [(k, year, v) for k, v in user_listen_counts.items()])
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting most prominent colors:", exc_info=True)


def insert_playlists(year, troi_patch_slug, import_file):
    connection = db.engine.raw_connection()
    query = """
        INSERT INTO statistics.year_in_music(user_id, year, data)
             SELECT "user".id
                  , playlists::jsonb
               FROM (VALUES %s) AS t(user_name, year, playlists)
               JOIN "user"
                 ON "user".musicbrainz_id = user_name
        ON CONFLICT (user_id)
      DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
        """

    data = []
    coverart_data = []
    with open(import_file, "r") as f:
        while True:
            user_name = f.readline()
            if user_name == "":
                break

            user_name = user_name.strip()
            playlist_mbid = f.readline().strip()
            jspf = f.readline().strip()
            jspf_obj = ujson.loads(jspf)
            coverart = get_coverart_for_playlist(jspf_obj)
            coverart_data.append((user_name, ujson.dumps({
                f"playlist-{troi_patch_slug}-coverart": coverart
            })))

            data.append((user_name, year, ujson.dumps({
                f"playlist-{troi_patch_slug}": {
                    "mbid": playlist_mbid,
                    "jspf": jspf_obj
                }
            })))

    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, data)
        connection.commit()
        # Coverart
        with connection.cursor() as cursor:
            execute_values(cursor, query, coverart_data)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting playlist/%s:" % troi_patch_slug, exc_info=True)


def get_coverart_for_playlist(playlist_jspf):
    tracks = playlist_jspf.get('playlist', {}).get('track', [])
    track_recording_mbids = [os.path.basename(track['identifier']) for track in tracks]

    if not track_recording_mbids:
        return {}

    query = """SELECT recording_mbid::text
                    , release_mbid::text
                 FROM mbid_mapping_metadata
                WHERE recording_mbid in :recording_mbids"""

    recording_mbid_to_release_mbid = {}
    with timescale.engine.connect() as connection:
        res = connection.execute(sqlalchemy.text(query), {"recording_mbids": tuple(track_recording_mbids)})
        for row in res.fetchall():
            recording_mbid = row["recording_mbid"]
            release_mbid = row["release_mbid"]
            recording_mbid_to_release_mbid[recording_mbid] = release_mbid

    coverart = get_coverart_for_top_releases(list(recording_mbid_to_release_mbid.values()))
    recording_mbid_to_coverart = {}
    for recording_mbid, release_mbid in recording_mbid_to_release_mbid.items():
        if release_mbid in coverart:
            recording_mbid_to_coverart[recording_mbid] = coverart[release_mbid]
    return recording_mbid_to_coverart


def caa_id_to_archive_url(release_mbid, caa_id):
    return f"https://archive.org/download/mbid-{release_mbid}/mbid-{release_mbid}-{caa_id}_thumb500.jpg"


def get_coverart_for_top_releases(release_mbids):
    """Use the CAA database connection to find coverart for each release
    1. Get release id and releasegroup id for each release (also considering release mbid redirects)
    2. Get coverart for these releases
    3. For releases with no cover art, see if any other release in their releasegroup has coverarat
    """

    if musicbrainz_db.engine is None:
        current_app.logger.warning("get_coverart_for_top_releases: No connection to MusicBrainz database")
        return {}

    if not release_mbids:
        return {}

    release_coverart = {}
    release_id_to_mbid = {}
    release_mbid_to_release_group_id = {}
    with musicbrainz_db.engine.connect() as connection:
        query = """SELECT release_gid_redirect.gid::text
                        , new_id
                        , release.release_group
                     FROM release_gid_redirect
                     JOIN release
                       ON release.id = new_id
                    WHERE release_gid_redirect.gid IN :release_mbids"""
        res = connection.execute(sqlalchemy.text(query), {"release_mbids": tuple(release_mbids)})
        for row in res.fetchall():
            release_id_to_mbid[row["new_id"]] = row["gid"]
            release_mbid_to_release_group_id[row["gid"]] = row["release_group"]
        query = """SELECT gid::text
                        , id
                        , release_group
                     FROM release
                    WHERE gid IN :release_mbids"""
        res = connection.execute(sqlalchemy.text(query), {"release_mbids": tuple(release_mbids)})
        for row in res.fetchall():
            release_id_to_mbid[row["id"]] = row["gid"]
            release_mbid_to_release_group_id[row["gid"]] = row["release_group"]

        if not release_id_to_mbid:
            # sometimes we might not find a release in the database (e.g. running on an out of date db replica)
            return {}

        # We need to know what the release mbid was that we passed in which gave us this rgid
        release_group_id_to_release_mbid = {v: k for k, v in release_mbid_to_release_group_id.items()}

        # Front coverart
        query = """SELECT id
                        , release
                     FROM cover_art_archive.index_listing
                    WHERE release in :release_ids
                      AND is_front = 't';
        """
        res = connection.execute(sqlalchemy.text(query), {"release_ids": tuple(release_id_to_mbid.keys())})
        for row in res.fetchall():
            release_id = row["release"]
            caa_id = row["id"]
            release_mbid = release_id_to_mbid[release_id]
            caa_url = caa_id_to_archive_url(release_mbid, caa_id)
            release_coverart[release_mbid] = caa_url

        unmatched_release_group_ids = [release_mbid_to_release_group_id[rmbid]
                                       for rmbid in release_mbids
                                       if rmbid not in release_coverart and rmbid in release_mbid_to_release_group_id]

        # Release mbids which didn't have coverart - find their releasegroup and then see if there is a release with coverart
        # https://github.com/metabrainz/artwork-redirect/blob/90ff5c7b/artwork_redirect/request.py#L124
        query = """SELECT DISTINCT ON (release.release_group)
          release_group.id as release_group_id
        , release.gid::text AS release_mbid
        , index_listing.id as caa_id
        FROM cover_art_archive.index_listing
        JOIN musicbrainz.release
          ON musicbrainz.release.id = cover_art_archive.index_listing.release
        JOIN musicbrainz.release_group
          ON release_group.id = release.release_group
        LEFT JOIN (
          SELECT release, date_year, date_month, date_day
          FROM musicbrainz.release_country
          UNION ALL
          SELECT release, date_year, date_month, date_day
          FROM musicbrainz.release_unknown_country
        ) release_event ON (release_event.release = release.id)
        FULL OUTER JOIN cover_art_archive.release_group_cover_art
        ON release_group_cover_art.release = musicbrainz.release.id
        WHERE release_group.id in :release_group_ids
        AND is_front = true
        ORDER BY release.release_group, release_group_cover_art.release,
          release_event.date_year, release_event.date_month,
          release_event.date_day"""
        if unmatched_release_group_ids:
            res = connection.execute(sqlalchemy.text(query), {"release_group_ids": tuple(unmatched_release_group_ids)})
            for row in res.fetchall():
                caa_id = row["caa_id"]
                release_group_id = row["release_group_id"]
                release_mbid = row["release_mbid"]
                # Use the release mbid that was passed into the method as the returned key, even if this isn't actually
                # the release that has the covert art
                original_release_mbid = release_group_id_to_release_mbid[release_group_id]
                caa_url = caa_id_to_archive_url(release_mbid, caa_id)
                release_coverart[original_release_mbid] = caa_url

    return release_coverart


def handle_coverart(user_id, year, key, data):
    with db.engine.connect() as connection:
        connection.execute(
            sqlalchemy.text("""
            INSERT INTO statistics.year_in_music (user_id, year, data)
                 VALUES (:user_id, :year, jsonb_build_object(:stat_type,:data :: jsonb))
            ON CONFLICT (user_id, year)
          DO UPDATE SET data = statistics.year_in_music.data || EXCLUDED.data
            """),
            {"user_id": user_id, "year": year, "stat_type": key, "data": ujson.dumps(data)}
        )


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
