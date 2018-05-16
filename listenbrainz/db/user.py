
import logging

import uuid

import sqlalchemy

from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz import config


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
            connection.execute(sqlalchemy.text("""
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


USER_GET_COLUMNS = ['id', 'created', 'musicbrainz_id', 'auth_token', 'last_login', 'latest_import']


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
            SELECT {columns}
              FROM "user"
             WHERE id = :id
        """.format(columns=','.join(USER_GET_COLUMNS))), {"id": id})
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
            SELECT {columns}
              FROM "user"
             WHERE LOWER(musicbrainz_id) = LOWER(:mb_id)
        """.format(columns=','.join(USER_GET_COLUMNS))), {"mb_id": musicbrainz_id})
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
            SELECT {columns}
              FROM "user"
             WHERE auth_token = :auth_token
        """.format(columns=','.join(USER_GET_COLUMNS))), {"auth_token": token})
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


def update_last_login(musicbrainz_id):
    """ Update the value of last_login field for user with specified MusicBrainz ID

    Args:
        musicbrainz_id (str): MusicBrainz username of a user
    """

    with db.engine.connect() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET last_login = NOW()
                 WHERE musicbrainz_id = :musicbrainz_id
                """), {
                    "musicbrainz_id": musicbrainz_id,
            })
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException("Couldn't update last_login: %s" % str(err))


def update_latest_import(musicbrainz_id, ts):
    """ Update the value of latest_import field for user with specified MusicBrainz ID

    Args:
        musicbrainz_id (str): MusicBrainz username of user
        ts (int): Timestamp value with which to update the database
    """

    with db.engine.connect() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                   SET latest_import = to_timestamp(:ts)
                 WHERE musicbrainz_id = :musicbrainz_id
                """), {
                    'ts': ts,
                    'musicbrainz_id': musicbrainz_id
                })
        except sqlalchemy.exc.ProgrammingError as e:
            logger.error(e)
            raise DatabaseException


def increase_latest_import(musicbrainz_id, ts):
    """Increases the latest_import field for user with specified MusicBrainz ID"""
    user = get_by_mb_id(musicbrainz_id)
    if ts > int(user['latest_import'].strftime('%s')):
        update_latest_import(musicbrainz_id, ts)


def reset_latest_import(musicbrainz_id):
    """Resets the latest_import field for user with specified MusicBrainz ID to 0"""
    user = get_by_mb_id(musicbrainz_id)
    update_latest_import(musicbrainz_id, 0)


def get_users_with_uncalculated_stats():
    """ Returns users whose stats have not been calculated by the stats calculation process
        yet. This means that the user must have logged-in in the last
        config.STATS_CALCULATION_LOGIN_TIME days and her stats must not have already
        been calculated in this interval.

        Returns:
            A list of dicts each of the form
            {
                'id' (int): the row ID of the user,
                'musicbrainz_id' (str): the musicbrainz_id of the user
            }
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                SELECT pu.id, pu.musicbrainz_id
                  FROM public."user" pu
             LEFT JOIN statistics.user su
                    ON pu.id = su.user_id
                 WHERE pu.last_login >= NOW() - INTERVAL ':x days'
                   AND (su.last_updated IS NULL OR su.last_updated < NOW() - INTERVAL ':y days')
                """), {
                    'x': config.STATS_CALCULATION_LOGIN_TIME,
                    'y': config.STATS_CALCULATION_INTERVAL,
                })

        return [dict(row) for row in result]


def get_all_users(columns=None):
    """ Returns a list of all users in the database

        Args:
            columns: a list of columns to be returned for each user

        Returns: if columns is None, A list of dicts of the following format for each user
            {
                'id': int
                'musicbrainz_id': string
                'created': datetime.datetime
                'auth_token': uuid
                'last_login': datetime.datetime
                'latest_import': datetime.datetime
            }

            otherwise, a list of dicts for each user with only the columns passed as argument
    """

    if columns is None:
        columns = USER_GET_COLUMNS

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
                SELECT {columns}
                  FROM "user"
              ORDER BY id
            """.format(columns=', '.join(columns))))

        return [dict(row) for row in result]


def delete(id):
    """ Delete the user with specified row ID from the database.

    Note: this deletes all statistics and api_compat sessions and tokens
    associated with the user also.

    Args:
        id (int): the row ID of the listenbrainz user
    """
    with db.engine.connect() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                DELETE FROM "user"
                      WHERE id = :id
                """), {
                    'id': id,
                })
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException("Couldn't delete user: %s" % str(err))
