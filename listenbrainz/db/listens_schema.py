"""Schema setup for the user-partitioned listens database."""

import os
import re

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
    CREATE TABLE IF NOT EXISTS listen_p{index:03d}
    PARTITION OF listen FOR VALUES WITH (MODULUS {modulus}, REMAINDER {index})
"""


PARTITION_BOUND_RE = re.compile(r"MODULUS\s+(\d+)\s*,\s*REMAINDER\s+(\d+)", re.IGNORECASE)


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


def _existing_partitions(cur):
    """ Return (modulus, count) of the existing hash partitions of the listen table. """
    cur.execute("""
        SELECT pg_get_expr(c.relpartbound, c.oid)
          FROM pg_inherits i
          JOIN pg_class c ON c.oid = i.inhrelid
         WHERE i.inhparent = 'listen'::regclass
    """)
    bounds = [row[0] for row in cur.fetchall()]  # FOR VALUES WITH (modulus 256, remainder 3)
    if not bounds:
        return None, 0
    moduli = set()
    for bound in bounds:
        match = PARTITION_BOUND_RE.search(bound)
        if match is None:
            raise click.ClickException(f"listen table has a partition that is not a hash partition: {bound}")
        moduli.add(int(match.group(1)))
    if len(moduli) != 1:
        raise click.ClickException(f"listen table has partitions with mixed moduli: {sorted(moduli)}")
    return moduli.pop(), len(bounds)


def create_schema(partition_count):
    logger = current_app.logger
    with connect_target() as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('listen')")
        if cur.fetchone()[0] is None:
            cur.execute(_read_sql(CREATE_TYPES_SQL_FILE))
            cur.execute(_read_sql(CREATE_TABLES_SQL_FILE))
            cur.execute(_read_sql(CREATE_PRIMARY_KEYS_SQL_FILE))
            logger.info("created listen table")
        else:
            logger.info("listen table already exists")

        cur.execute("SELECT to_regclass('listen_delete_metadata')")
        if cur.fetchone()[0] is None:
            cur.execute(_read_sql(os.path.join(ADMIN_SQL_DIR, "updates", "2026-09-16-add-deletion-tables.sql")))

        modulus, existing = _existing_partitions(cur)
        if existing and modulus != partition_count:
            raise click.ClickException(
                f"listen table already has {existing} partitions with modulus {modulus}, "
                f"refusing to create partitions with modulus {partition_count}"
            )
        if existing:
            logger.info("listen table already has %d of %d partitions, creating the missing ones", existing, partition_count)
        for index in range(partition_count):
            cur.execute(CREATE_PARTITION_SQL.format(index=index, modulus=partition_count))
        conn.commit()
    logger.info("listen table has %d partitions", partition_count)


def create_indexes():
    with connect_target() as conn, conn.cursor() as cur:
        cur.execute(_read_sql(CREATE_INDEXES_SQL_FILE))
        conn.commit()
    current_app.logger.info("created listen indexes")
