""" This file contains handler functions for rabbitmq messages we
receive from the Spark cluster.
"""
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats

from flask import current_app


def handle_user_artist(data):
    """ Take artist stats for a user and save it in the database.
    """
    musicbrainz_id = data['musicbrainz_id']
    user = db_user.get_by_mb_id(musicbrainz_id)
    if not user:
        return
    artists = data['artist_stats']
    artist_count = data['artist_count']
    db_stats.insert_user_stats(user['id'], artists, {}, {}, artist_count)
