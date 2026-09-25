from datetime import datetime

from brainzutils import cache

from data.model.external_service import ExternalServiceType
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT
from listenbrainz.db import user as db_user, listens as listens_db, listens_importer, playlist as db_playlist
from listenbrainz.webserver.listens_cache import invalidate_user_listen_caches


def delete_user(db_conn, ts_conn, user_id: int, created: datetime):
    """ Delete an account and its listens DB history. Timescale listens are retained.

    Args:
        user_id: the LB row ID of the user
        created: listens created before this timestamp are deleted
    """
    listens_db.delete_user(user_id, created)
    db_playlist.delete_playlists_by_user_id(ts_conn, user_id)

    db_user.delete(db_conn, user_id)
    db_conn.commit()


def delete_listens_history(db_conn, user_id: int, created: datetime):
    """ Delete a user's history in the listens DB and retain its deletion record.

    Args:
        user_id: the LB row ID of the user
        created: listens created before this timestamp are deleted
    """
    listens_db.delete_user(user_id, created)
    cache.delete(REDIS_USER_LISTEN_COUNT + str(user_id))
    invalidate_user_listen_caches(user_id)
    listens_importer.update_latest_listened_at(db_conn, user_id, ExternalServiceType.LASTFM, 0)
    db_conn.commit()
