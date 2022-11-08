import sqlalchemy
from listenbrainz import db
from listenbrainz.db.exceptions import DatabaseException


DEFAULT_TIMEZONE = "UTC"


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
        timezones = [(row.name, row.utc_offset) for row in result.fetchall()]
        timezones = standardize_timezone(timezones)
        return timezones


def get(user_id: int):
    """ Get user settings with the row ID of the user in the DB.
    Args:
        user_id (int): the row ID of the user in the DB
    Returns:
        user settings (dict) where
        timezone_name: user selected local timezone, with default value "UTC".
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
            row = result.mappings().first()
            if row:
                row = dict(row)
                if not row["timezone_name"]:
                    row["timezone_name"] = DEFAULT_TIMEZONE
                return row
            return {"timezone_name": DEFAULT_TIMEZONE}
        except sqlalchemy.exc.ProgrammingError as err:
            raise DatabaseException(
                "Couldn't get user's setting: %s" % str(err))


def set_timezone(user_id: int, timezone_name: str):
    """ Set user's timezone. Update user timezone if the row exists. Otherwise insert a new row.
    Args:
        user_id (int): the row ID of the user in the DB
        timezone_name (str): the user selected timezone name

    """
    with db.engine.begin() as connection:
        try:
            connection.execute(sqlalchemy.text("""
                INSERT INTO user_setting (user_id, timezone_name)
                VALUES (:user_id, :timezone_name)
                ON CONFLICT (user_id)
                DO 
                    UPDATE SET timezone_name = :timezone_name
                """), {
                "user_id": user_id,
                "timezone_name": timezone_name,
            })
        except sqlalchemy.exc.ProgrammingError as err:
            raise DatabaseException(
                "Couldn't update user's timezone: %s" % str(err))


def standardize_timezone(timezones):
    """ Standardize timezone format retrieved by pg for better display 
        E.x., Convert "Africa/Adnodjan (3:00:00)" to "Africa/addis_Ababa (+3:00:00 GMT)"
        Convert "America/Adak (-1day, 15:00:00)" to "America/Adak (-9:00:00 GMT)"
    Args:
        timezones (list): timezones retrieved by pg
    return:
        list of tuples: [(Africa/Abidjan, +0:00:00 GMT), (Africa/addis_Ababa, +3:00:00 GMT),...]

    """
    result = []
    for (name, offset) in timezones:
        if offset.days > -1:
            result.append((name, "+" + str(offset) + " GMT"))
        else:
            result.append((name, str(offset.seconds//3600 - 24) + ":00:00 GMT"))
    return result


def update_troi_prefs(user_id: int, export_to_spotify: bool):
    """ Update troi preferences for the given user """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO user_setting (user_id, troi)
                 VALUES (:user_id, jsonb_build_object('export_to_spotify', :export_to_spotify))
            ON CONFLICT (user_id)
              DO UPDATE 
                    SET troi = EXCLUDED.troi
        """), {"user_id": user_id, "export_to_spotify": export_to_spotify})


def get_troi_prefs(user_id: int):
    """ Retrieve troi preferences for the given user """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT troi
              FROM user_setting
             WHERE user_id = :user_id
        """), {"user_id": user_id})
        row = result.mappings().first()
        return dict(row) if row else None
