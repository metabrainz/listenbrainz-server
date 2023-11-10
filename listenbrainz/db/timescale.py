from typing import Optional

import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import time
import psycopg2

# The schema version of the timescale database (tables created
# from ./admin/timescale/create-tables.sql). This includes user playlists
# and mbid mappings.
# Listens are tracked with `listenstore.LISTENS_DUMP_SCHEMA_VERSION`
# This value must be incremented after schema changes on tables that are included in the
# public dump
SCHEMA_VERSION_TIMESCALE = 7

engine: Optional[sqlalchemy.engine.Engine] = None

DUMP_DEFAULT_THREAD_COUNT = 4


def init_db_connection(connect_str):
    """Initializes timescale connection using the specified Flask app.

    Configuration file must contain `SQLALCHEMY_DATABASE_URI` key. See
    https://pythonhosted.org/Flask-SQLAlchemy/config.html#configuration-keys
    for more info.
    """
    global engine
    if not connect_str:
        return

    while True:
        try:
            engine = create_engine(connect_str, poolclass=NullPool)
            break
        except psycopg2.OperationalError as e:
            print("Couldn't establish connection to timescale: {}".format(str(e)))
            print("Sleeping 2 seconds and trying again...")
            time.sleep(2)


def run_sql_script(sql_file_path):
    with open(sql_file_path) as sql, engine.begin() as connection:
        connection.execute(text(sql.read()))


def run_sql_script_without_transaction(sql_file_path):
    with open(sql_file_path) as sql, engine.connect() as connection:
        connection.connection.set_isolation_level(0)
        lines = sql.read().splitlines()
        retries = 0
        while True:
            try:
                # no-op because of isolation level setup above but adding to suppress SQLAlchemy autocommit warnings
                with connection.begin():
                    for line in lines:
                        # TODO: Not a great way of removing comments. The alternative is to catch
                        # the exception sqlalchemy.exc.ProgrammingError "can't execute an empty query"
                        if line and not line.startswith("--"):
                            connection.execute(text(line))
                break
            except sqlalchemy.exc.ProgrammingError as e:
                print("Error: {}".format(e))
                return False
            except sqlalchemy.exc.OperationalError:
                print("Trapped template1 access error, FFS! Sleeping, trying again.")
                retries += 1
                if retries == 5:
                    raise
                time.sleep(1)
                continue
            finally:
                connection.connection.set_isolation_level(1)
        return True


def run_sql_query_without_transaction(sql_query):
    with engine.connect() as connection:
        connection.connection.set_isolation_level(0)
        try:
            for line in sql_query:
                if line and not line.startswith("--"):
                    connection.execute(text(line))
                    print("EXECUTE: %s" % line)
        except sqlalchemy.exc.ProgrammingError as e:
            print("Error: {}".format(e))
            return False
        finally:
            connection.connection.set_isolation_level(1)
            connection.close()
        return True


def create_test_timescale_connect_strings():
    db_name = "listenbrainz_ts_test"
    db_user = "listenbrainz_ts_test"
    return {
        "DB_CONNECT": f"postgresql://{db_user}:listenbrainz_ts@lb_db/{db_name}",
        "DB_CONNECT_ADMIN": "postgresql://postgres:postgres@lb_db/postgres",
        "DB_CONNECT_ADMIN_LB": f"postgresql://postgres:postgres@lb_db/{db_name}",
        "DB_NAME": db_name,
        "DB_USER": db_user
    }
