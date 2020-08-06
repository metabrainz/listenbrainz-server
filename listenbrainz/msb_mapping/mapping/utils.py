from time import asctime
import psycopg2
from psycopg2.extras import execute_values


def create_schema(conn):
    '''
        Create the relations schema if it doesn't already exist
    '''

    try:
        with conn.cursor() as curs:
            print(asctime(), "create schema")
            curs.execute("CREATE SCHEMA IF NOT EXISTS mapping")
            conn.commit()
    except OperationalError:
        print(asctime(), "failed to create schema 'mapping'")
        conn.rollback()


def insert_rows(curs, table, values): 
 
    query = "INSERT INTO " + table + " VALUES %s" 
    try: 
        execute_values(curs, query, values, template=None) 
    except psycopg2.OperationalError as err: 
        print("failed to insert rows", err)
