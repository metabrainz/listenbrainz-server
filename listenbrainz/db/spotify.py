from listenbrainz import db
import sqlalchemy


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
