import psycopg2
from flask import current_app
from psycopg2.extras import execute_values

from listenbrainz.db import timescale


def insert(query, values):
    connection = timescale.engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            execute_values(cursor, query, values)
        connection.commit()
    except psycopg2.errors.OperationalError:
        connection.rollback()
        current_app.logger.error("Error while inserting popularity data:", exc_info=True)


def insert_recording(data):
    """ Insert recording popularity data. """
    query = "INSERT INTO popularity.recording (recording_mbid, total_listen_count, total_user_count) VALUES %s"
    values = [(r["recording_mbid"], r["total_listen_count"], r["total_user_count"]) for r in data]
    insert(query, values)


def insert_artist(data):
    """ Insert artist popularity data. """
    query = "INSERT INTO popularity.artist (artist_mbid, total_listen_count, total_user_count) VALUES %s"
    values = [(r["artist_mbid"], r["total_listen_count"], r["total_user_count"]) for r in data]
    insert(query, values)


def insert_release(data):
    """ Insert release popularity data. """
    query = "INSERT INTO popularity.release (release_mbid, total_listen_count, total_user_count) VALUES %s"
    values = [(r["release_mbid"], r["total_listen_count"], r["total_user_count"]) for r in data]
    insert(query, values)


def insert_top_recording(data):
    """ Insert artist's top recordings data. """
    query = "INSERT INTO popularity.top_recording (artist_mbid, recording_mbid, total_listen_count, total_user_count) VALUES %s"
    values = [(r["artist_mbid"], r["recording_mbid"], r["total_listen_count"], r["total_user_count"]) for r in data]
    insert(query, values)


def insert_top_release(data):
    """ Insert artist's top releases data. """
    query = "INSERT INTO popularity.top_release (artist_mbid, release_mbid, total_listen_count, total_user_count) VALUES %s"
    values = [(r["artist_mbid"], r["release_mbid"], r["total_listen_count"], r["total_user_count"]) for r in data]
    insert(query, values)
