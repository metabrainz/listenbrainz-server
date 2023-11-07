from typing import Optional

import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
import time
import psycopg2
import psycopg2.extras

# The schema version of the core database. This includes data in the "user" database
# (tables created from ./admin/sql/create-tables.sql) and includes user data,
# statistics, feedback, and results of user interaction on the site.
# This value must be incremented after schema changes on tables that are included in the
# public dump
SCHEMA_VERSION_CORE = 8

engine: Optional[sqlalchemy.engine.Engine] = None

DUMP_DEFAULT_THREAD_COUNT = 4

# Load the UUID extension
psycopg2.extras.register_uuid()


def init_db_connection(connect_str):
    """Initializes database connection using the specified Flask app.

    Configuration file must contain `SQLALCHEMY_DATABASE_URI` key. See
    https://pythonhosted.org/Flask-SQLAlchemy/config.html#configuration-keys
    for more info.
    """
    global engine
    while True:
        try:
            engine = create_engine(connect_str, poolclass=NullPool)
            break
        except psycopg2.OperationalError as e:
            print("Couldn't establish connection to db: {}".format(str(e)))
            print("Sleeping 2 seconds and trying again...")
            time.sleep(2)


def run_sql_script(sql_file_path):
    with open(sql_file_path) as sql, engine.begin() as connection:
        connection.execute(text(sql.read()))


def run_sql_script_without_transaction(sql_file_path):
    with open(sql_file_path) as sql, engine.connect() as connection:
        connection.connection.set_isolation_level(0)
        lines = sql.read().splitlines()
        try:
            for line in lines:
                # TODO: Not a great way of removing comments. The alternative is to catch
                # the exception sqlalchemy.exc.ProgrammingError "can't execute an empty query"
                if line and not line.startswith("--"):
                    connection.execute(text(line))
        except sqlalchemy.exc.ProgrammingError as e:
            print("Error: {}".format(e))
            return False
        finally:
            connection.connection.set_isolation_level(1)
            connection.close()
        return True


def is_development_db():

    with engine.begin() as connection:
        try:
            for row in connection.execute(text("SELECT environment FROM database_environment")):
                if row["environment"] is not None and row["environment"] != "" and row["environment"] == "development":
                    print("database is a development database.")
                    return True
                else:
                    print("database is NOT a development database.")
                    return False

            print("Could not fetch row from database_environment table to determine DB environment")
            return False
        except sqlalchemy.exc.ProgrammingError as err:
            # Any exception thrown makes it clear that this isn't a properly setup dev DB
            print("Could not fetch environment from the database_environment table. Does the table exist?")
            return False
