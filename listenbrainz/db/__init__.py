import time
from typing import Optional

import psycopg2
import psycopg2.extras
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

engine: Optional[sqlalchemy.engine.Engine] = None

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


def create_test_database_connect_strings():
    db_name = "listenbrainz_test"
    db_user = "listenbrainz_test"
    return {"DB_CONNECT": f"postgresql://{db_user}:listenbrainz@lb_db:5432/{db_name}",
            "DB_CONNECT_ADMIN": "postgresql://postgres:postgres@lb_db/postgres",
            "DB_CONNECT_ADMIN_LB": f"postgresql://postgres:postgres@lb_db/{db_name}",
            "DB_NAME": db_name,
            "DB_USER": db_user}
