import sys
from time import asctime

import psycopg2
from psycopg2.extras import execute_values

CRON_LOG_FILE = "lb-cron.log"


def create_schema(conn):
    '''
        Create the relations schema if it doesn't already exist
    '''

    try:
        with conn.cursor() as curs:
            log("create schema")
            curs.execute("CREATE SCHEMA IF NOT EXISTS mapping")
            conn.commit()
    except OperationalError:
        log("failed to create schema 'mapping'")
        conn.rollback()


def create_stats_table(curs):
    '''
        Create the stats table if it doesn't exist
    '''
    curs.execute("""CREATE TABLE IF NOT EXISTS mapping.mapping_stats 
                                 (stats    JSONB,
                                  created  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())""")


def insert_rows(curs, table, values): 
    '''
        Helper function to insert a large number of rows into postgres in one go.
    '''
 
    query = "INSERT INTO " + table + " VALUES %s" 
    execute_values(curs, query, values, template=None) 


def log(*args):
    '''
        Super simple logging function that prepends timestamps. Did I mention I had python's logging module?
    '''
    print(asctime(), *args)
    sys.stdout.flush()
