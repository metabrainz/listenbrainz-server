from listenbrainz import db, utils
import sqlalchemy


def add_update_error(user_id, error_message):
    """ Add an error message to be shown to the user, thereby setting the user as inactive.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        error_message (str): the user-friendly error message to be displayed
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE listens_importer
               SET last_updated = now()
                 , error_message = :error_message
              WHERE user_id = :user_id
                AND service = 'spotify'
        """), {
            "user_id": user_id,
            "error_message": error_message
        })


def update_last_updated(user_id):
    """ Update the last_updated field for the user with specified LB user_id.

    Args:
        user_id (int): the ListenBrainz row ID of the user
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE listens_importer
                SET last_updated = now()
                , error_message = NULL
            WHERE user_id = :user_id
        """), {
            "user_id": user_id,
        })


def update_latest_listened_at(user_id, timestamp):
    """ Update the timestamp of the last listen imported for the user with
    specified LB user ID.

    Args:
        user_id (int): the ListenBrainz row ID of the user
        timestamp (int): the unix timestamp of the latest listen imported for the user
    """
    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE listens_importer
               SET latest_listened_at = :timestamp
             WHERE user_id = :user_id
               AND service = 'spotify'
            """), {
                'user_id': user_id,
                'timestamp': utils.unix_timestamp_to_datetime(timestamp),
            })


def get_active_users_to_process():
    """ Returns a list of users whose listens should be imported from Spotify.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT external_service_oauth.user_id
                 , "user".musicbrainz_id
                 , "user".musicbrainz_row_id
                 , access_token
                 , refresh_token
                 , listens_importer.last_updated
                 , token_expires
                 , token_expires < now() as token_expired
                 , scopes
                 , latest_listened_at
                 , error_message
              FROM external_service_oauth
              JOIN "user"
                ON "user".id = external_service_oauth.user_id
              JOIN listens_importer
                ON listens_importer.external_service_oauth_id = external_service_oauth.id
              WHERE external_service_oauth.service = 'spotify'
                AND error_message IS NULL
          ORDER BY latest_listened_at DESC NULLS LAST
        """))
        return [dict(row) for row in result.fetchall()]


def get_user_import_details(user_id):
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT external_service_oauth.user_id
                 , listens_importer.id
                 , listens_importer.last_updated
                 , latest_listened_at
                 , error_message
              FROM external_service_oauth
   LEFT OUTER JOIN listens_importer
                ON listens_importer.external_service_oauth_id = external_service_oauth.id
             WHERE external_service_oauth.user_id = :user_id
               AND external_service_oauth.service = 'spotify'
            """), {
                'user_id': user_id,
            })
        if result.rowcount > 0:
            return dict(result.fetchone())
    return None
