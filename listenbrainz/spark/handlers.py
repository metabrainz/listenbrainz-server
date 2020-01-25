import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats

from flask import current_app


def handle_user_artist(data):
    musicbrainz_id = data['musicbrainz_id']
    user = db_user.get_by_mb_id(musicbrainz_id)
    if not user:
        return
    artists = data['artist_stats']
    artist_count = data['artist_count']
    db_stats.insert_user_stats(user['id'], artists, {}, {}, artist_count)
    current_app.logger.info('Processed artist data for %s', musicbrainz_id)


def handle_user_release(data):
    pass #TODO: add releases

def handle_user_track(data):
    pass #TODO: add track
