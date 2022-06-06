import sqlalchemy
from datetime import datetime, timedelta
from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def get_pg_timezone():
    """ Get list of time zones PostgreSQL supports.

    Returns:
        list of tuple('zone_name', 'utc_offset')
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT * FROM pg_timezone_names
            ORDER BY name
        """))
        timezones = [(row["name"], row["utc_offset"]) for row in result.fetchall()]
        timezones = standardize_timezone(timezones)
        return timezones


def get(user_id: int):
    """Get user setting with the row ID of the user in the DB, or create if there's setting history.
    Args:
        user_id (int): the row ID of the user in the DB
    Returns:
        zone_name (str): the user selected timezone name. If not selected by user, return 'UTC'
    """
    with db.engine.connect() as connection:
        try:
            result = connection.execute(sqlalchemy.text("""
                SELECT timezone_name
                FROM user_setting
                WHERE user_id = :user_id
            """), {
                "user_id": user_id,
            })
            if result.rowcount:
                return dict(result.fetchone())
            return None
            # print("get from db...user_timezone: ", row)
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException(
                "Couldn't get user's timezone: %s" % str(err))

def create(user_id: int, timezone_name: str = "UTC"):
    """Create setting for user

    Args:
        user_id (int): the row ID of the user in the DB
        timezone_name(str): with default as "UTC

    Returns:
        ID of newly created user setting.
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO user_setting (user_id, timezone_name)
                 VALUES (:user_id, :timezone_name)
              RETURNING id
        """), {
            "user_id": user_id,
            "timezone_name": timezone_name,
        })
        return result.fetchone()["id"]

   
def get_or_create(user_id: int):
    """Get user setting with the row ID of the user in the DB, or create if there's setting history.
    Args:
        user_id (int): the row ID of the user in the DB
    Returns:
        dict: user settings
    """
    user_settings = get(user_id)
    if not user_settings:
        create(user_id)
        user_settings = get(user_id)
    return user_settings

def update_timezone(user_id: int, timezone_name:str):
    """update user's timezone
    Args:
        user_id (int): the row ID of the user in the DB
        zone_name (str): the user selected timezone name

    """
    with db.engine.connect() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                UPDATE "user_setting"
                SET timezone_name = :timezone_name
                WHERE user_id = :user_id
                """), {
                "user_id": user_id,
                "timezone_name": timezone_name,
            })
            # print('db: ',get_user_timezone(user_id) )
        except sqlalchemy.exc.ProgrammingError as err:
            logger.error(err)
            raise DatabaseException(
                "Couldn't update user's timezone: %s" % str(err))

def standardize_timezone(timezones):
    """standardize timezone format
    Args:
        timezone (list): timezone retrived by pg
    return:
        list of tuples: [(Africa/Abidjan, +0:00:00 GMT), (Africa/addis_Ababa, +3:00:00 GMT),...]

    """
    result = []
    for (name, offset) in timezones:
        if offset.days > -1:
            result.append((name, "+" + str(offset) + " GMT"))
        else:
            # result.append((name, str(int(str(offset)[8:10]) - 24) + ":00:00"))
            result.append((name, str(offset.seconds//3600 - 24) + ":00:00 GMT"))
    return result