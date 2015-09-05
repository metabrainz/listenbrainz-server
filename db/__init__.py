import psycopg2
import psycopg2.extras
import psycopg2.extensions
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

import logging


# This value must be incremented after schema changes on replicated tables!
SCHEMA_VERSION = 2

# Be careful when importing `_connection` before init_connection function is
# called! In general helper functions like `create_cursor` or `commit` should
# be used. Feel free to add new ones if some functionality is missing.
_connection = None


def init_db_connection(dsn):
    global _connection
    try:
        _connection = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.DictCursor)
    except psycopg2.OperationalError as e:
        logging.error("Failed to initialize database connection: %s" % str(e))


def create_cursor():
    """Creates a new psycopg `cursor` object.

    See http://initd.org/psycopg/docs/connection.html#connection.cursor.
    """
    return _connection.cursor()


def commit():
    """Commits any pending transaction to the database.

    See http://initd.org/psycopg/docs/connection.html#connection.commit.
    """
    return _connection.commit()


def close_connection():
    _connection.close()


def run_sql_script(sql_file_path):
    with _connection.cursor() as cursor:
        with open(sql_file_path) as sql:
            cursor.execute(sql.read())
