from typing import List, Optional

from listenbrainz import db
import sqlalchemy


def get_active_users_to_process() -> List[dict]:
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
        return [row for row in result.mappings()]


def get_user_import_details(user_id: int) -> Optional[dict]:
    """ Return user's spotify linking details to display on connect services page

    Args:
        user_id (int): the ListenBrainz row ID of the user
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT listens_importer.user_id
                 , listens_importer.id
                 , listens_importer.last_updated
                 , latest_listened_at
                 , error_message
              FROM listens_importer
         LEFT JOIN external_service_oauth
                ON listens_importer.external_service_oauth_id = external_service_oauth.id
             WHERE listens_importer.user_id = :user_id
               AND listens_importer.service = 'spotify'
            """), {
                'user_id': user_id,
            })
        row = result.mappings().first()
        return dict(row) if row else None


def get_user(user_id: int) -> Optional[dict]:
    """ This get_user method is different from the one in external_service_oauth.py because
     here we join against the listens_importer table to fetch the latest_listened_at column.
     We need latest_listened_at column for using in the spotify_reader."""
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT external_service_oauth.user_id
                 , "user".musicbrainz_id
                 , "user".musicbrainz_row_id
                 , external_service_oauth.service
                 , external_user_id
                 , access_token
                 , refresh_token
                 , external_service_oauth.last_updated
                 , token_expires
                 , scopes
                 , latest_listened_at
                 , error_message
              FROM external_service_oauth
              JOIN "user"
                ON "user".id = external_service_oauth.user_id
         LEFT JOIN listens_importer
                ON listens_importer.external_service_oauth_id = external_service_oauth.id
             WHERE external_service_oauth.service = 'spotify'
               AND "user".id = :user_id
        """), {
            'user_id': user_id
        })
        return result.mappings().first()
