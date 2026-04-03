import sys
from time import asctime

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
from psycopg2.errors import OperationalError

CRON_LOG_FILE = "lb-cron.log"


def create_schema(conn):
    '''
        Create the relations schema if it doesn't already exist
    '''

    try:
        with conn.cursor() as curs:
            curs.execute("CREATE SCHEMA IF NOT EXISTS mapping")
            conn.commit()
    except OperationalError:
        conn.rollback()
        raise


def insert_rows(curs, table, values, cols=None):
    '''
        Helper function to insert a large number of rows into postgres in one go.
    '''

    if not isinstance(table, str) or not table:
        raise ValueError("table must be a non-empty string")

    table_sql = sql.SQL('.').join(sql.Identifier(part) for part in table.split('.'))

    if cols is not None and len(cols) > 0:
        cols_sql = sql.SQL(',').join(sql.Identifier(col) for col in cols)
        query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(table_sql, cols_sql)
        execute_values(curs, query, values, template=None)
    else:
        query = sql.SQL("INSERT INTO {} VALUES %s").format(table_sql)
        execute_values(curs, query, values, template=None)


def log(*args):
    '''
        Super simple logging function that prepends timestamps. Did I mention I hate python's logging module?
    '''
    print(asctime(), *args)
    sys.stdout.flush()
