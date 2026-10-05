"""Schema setup for the user-partitioned listens database."""

import os

import click
import psycopg2
from flask import current_app


ADMIN_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "admin", "listens")


CREATE_TABLES_SQL_FILE = os.path.join(ADMIN_SQL_DIR, "create_tables.sql")


CREATE_TYPES_SQL_FILE = os.path.join(ADMIN_SQL_DIR, "create_types.sql")


CREATE_PRIMARY_KEYS_SQL_FILE = os.path.join(ADMIN_SQL_DIR, "create_primary_keys.sql")


CREATE_INDEXES_SQL_FILE = os.path.join(ADMIN_SQL_DIR, "create_indexes.sql")


PARTITION_COUNT = 256


CREATE_PARTITION_SQL = """
    CREATE TABLE listen_p{index:03d}
    PARTITION OF listen FOR VALUES WITH (MODULUS {modulus}, REMAINDER {index})
"""


def _uri(name):
    # consul renders SERVICEDOESNOTEXIST_... when the database service is not registered and
    # KEYDOESNOTEXIST_... into the uri when one of its keys is missing
    uri = current_app.config.get(name)
    if not uri or uri.startswith("SERVICEDOESNOTEXIST") or "KEYDOESNOTEXIST" in uri:
        raise click.UsageError(f"{name} is not set in the config")
    return uri


def connect_target():
    return psycopg2.connect(_uri("SQLALCHEMY_LISTENS_URI"))


def _read_sql(path):
    with open(path) as f:
        return f.read()


def create_schema(partition_count):
    with connect_target() as conn, conn.cursor() as cur:
        cur.execute(_read_sql(CREATE_TYPES_SQL_FILE))
        cur.execute(_read_sql(CREATE_TABLES_SQL_FILE))
        cur.execute(_read_sql(CREATE_PRIMARY_KEYS_SQL_FILE))
        for index in range(partition_count):
            cur.execute(CREATE_PARTITION_SQL.format(index=index, modulus=partition_count))
        conn.commit()
    current_app.logger.info("created listen tables and %d partitions", partition_count)


def create_indexes():
    with connect_target() as conn, conn.cursor() as cur:
        cur.execute(_read_sql(CREATE_INDEXES_SQL_FILE))
        conn.commit()
    current_app.logger.info("created listen indexes")
