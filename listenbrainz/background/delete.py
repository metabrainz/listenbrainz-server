from datetime import datetime

from data.model.external_service import ExternalServiceType
from listenbrainz.webserver import timescale_connection
from listenbrainz.db import user as db_user, listens_importer


def delete_user(db_conn, user_id: int, created: datetime):
    """ Delete a user from ListenBrainz completely. First, drops
     the user's listens and then deletes the user from the database.

    Args:
        user_id: the LB row ID of the user
        created: listens created before this timestamp are deleted
    """
    timescale_connection._ts.delete(user_id, created)
    db_user.delete(db_conn, user_id)
    db_conn.commit()


def delete_listens_history(db_conn, user_id: int, created: datetime):
    """ Delete a user's listens from ListenBrainz completely.

    Args:
        user_id: the LB row ID of the user
        created: listens created before this timestamp are deleted
    """
    timescale_connection._ts.delete(user_id, created)
    listens_importer.update_latest_listened_at(db_conn, user_id, ExternalServiceType.LASTFM, 0)
    db_conn.commit()
