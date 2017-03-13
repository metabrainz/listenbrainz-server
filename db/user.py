import db
import uuid
import sqlalchemy
from db.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def create(musicbrainz_id):
    """Create a new user.

    Args:
        musicbrainz_id (str): MusicBrainz username of a user.

    Returns:
        ID of newly created user.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO "user" (musicbrainz_id, auth_token)
                 VALUES (:mb_id, :token)
              RETURNING id
        """), {
            "mb_id": musicbrainz_id,
            "token": str(uuid.uuid4()),
        })
        return result.fetchone()["id"]

def update_token(id):
    """Update a user's token to a new UUID

    Args:
        id (int) - the row id of the user to update
    """
    with db.engine.connect() as connection:
        try:
            result = connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET auth_token = :token
                 WHERE id = :id
            """), {
                "token": str(uuid.uuid4()),
                "id": id
            })
        except DatabaseException as e:
            logger.error(e)
            raise


def get(id):
    """Get user with a specified ID.

    Args:
        id (int): ID of a user.

    Returns:
        Dictionary with the following structure:
        {
            "id": <user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
            "auth_token": <authentication token>,
        }
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, musicbrainz_id, auth_token
              FROM "user"
             WHERE id = :id
        """), {"id": id})
        row = result.fetchone()
        return dict(row) if row else None


def get_by_mb_id(musicbrainz_id):
    """Get user with a specified MusicBrainz ID.

    Args:
        musicbrainz_id (str): MusicBrainz username of a user.

    Returns:
        Dictionary with the following structure:
        {
            "id": <user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
            "auth_token": <authentication token>,
        }
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, musicbrainz_id, auth_token
              FROM "user"
             WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)
        """), {"mb_id": musicbrainz_id})
        row = result.fetchone()
        return dict(row) if row else None



def get_by_token(token):
    """Get user with a specified authentication token.

    Args:
        token (str): Authentication token associated with user's account.

    Returns:
        Dictionary with the following structure:
        {
            "id": <user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
        }
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, musicbrainz_id
              FROM "user"
             WHERE auth_token = :auth_token
        """), {"auth_token": token})
        row = result.fetchone()
        return dict(row) if row else None


def get_user_count():
    """ Get total number of users in database.

    Returns:
        int: user count
    """

    with db.engine.connect() as connection:
        try:
            result = connection.execute(sqlalchemy.text("""
                SELECT count(*) AS user_count
                  FROM "user"
            """))
            row = result.fetchone()
            return row['user_count']
        except DatabaseException as e:
            logger.error(e)
            raise

def get_or_create(musicbrainz_id):
    """Get user with a specified MusicBrainz ID, or create if there's no account.

    Args:
        musicbrainz_id (str): MusicBrainz username of a user.

    Returns:
        Dictionary with the following structure:
        {
            "id": <user id>,
            "created": <account creation time>,
            "musicbrainz_id": <MusicBrainz username>,
            "auth_token": <authentication token>,
        }
    """
    user = get_by_mb_id(musicbrainz_id)
    if not user:
        create(musicbrainz_id)
        user = get_by_mb_id(musicbrainz_id)
    return user
