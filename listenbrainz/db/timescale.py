
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import time
import psycopg2

from listenbrainz import config

# This value must be incremented after schema changes on replicated tables!
SCHEMA_VERSION = 6

engine = None

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
    with open(sql_file_path) as sql:
        with engine.connect() as connection:
            connection.execute(sql.read())


def run_sql_script_without_transaction(sql_file_path):
    with open(sql_file_path) as sql:
        connection = engine.connect()
        connection.connection.set_isolation_level(0)
        lines = sql.read().splitlines()
        retries = 0
        while True:
            try:
                for line in lines:
                    # TODO: Not a great way of removing comments. The alternative is to catch
                    # the exception sqlalchemy.exc.ProgrammingError "can't execute an empty query"
                    if line and not line.startswith("--"):
                        connection.execute(line)
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
                connection.close()
        return True


def create_view_indexes():
    """ This function is needed since we need to create an index on a materialized view, whose
        name we need to query - its not a constant, thus it cannot be done in pure SQL.
    """

    admin_engine = create_engine(
        config.TIMESCALE_ADMIN_LB_URI, poolclass=NullPool)
    with admin_engine.connect() as connection:
        query = """SELECT materialization_hypertable_schema, materialization_hypertable_name
                     FROM timescaledb_information.continuous_aggregates
                    WHERE view_name = 'listen_count_30day'"""
        curs = connection.execute(query)
        row = curs.fetchone()
        if row is None:
            raise RuntimeError(
                "Cannot find materialized view name for listen_count view.")

        view_schema = row[0]
        view_name = row[1]
        if not view_name:
            raise RuntimeError(
                "Cannot find materialized view name for listen_count view.")

        query = """CREATE INDEX listened_at_bucket_user_name_ndx_listen_count_30day
                             ON %s.%s (listened_at_bucket, user_name)""" % (view_schema, view_name)
        try:
            connection.execute(query)
        except Exception as err:
            raise RuntimeError(
                "Cannot create index on materialized view of listen_count_30day")

        query = """CREATE INDEX user_name_ndx_listen_count_30day
                             ON %s.%s (user_name)""" % (view_schema, view_name)
        try:
            connection.execute(query)
        except Exception as err:
            raise RuntimeError(
                "Cannot create index on materialized view of listen_count_30day")
