import sqlalchemy

from listenbrainz import db


def add_dump_entry(timestamp, dump_type):
    """ Adds an entry to the data_dump table with specified time.

        Args:
            timestamp: the datetime to be added

        Returns:
            id (int): the id of the new entry added
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO data_dump (created, dump_type)
                 VALUES (:ts, :dump_type)
              RETURNING id
        """), {
            'ts': timestamp,
            'dump_type': dump_type
        })
        return result.fetchone().id


def get_dump_entries():
    """ Returns a list of all dump entries in the data_dump table
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, dump_type
              FROM data_dump
          ORDER BY created DESC
        """))

        return result.mappings().all()


def get_dump_entry(dump_id, dump_type=None):
    filters = ["id = :dump_id"]
    args = {"dump_id": dump_id}

    if dump_type is not None:
        filters.append("dump_type = :dump_type")
        args["dump_type"] = dump_type

    where_clause = " AND ".join(filters)
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, dump_type
              FROM data_dump
             WHERE """ + where_clause), args)
        return result.mappings().first()


def get_latest_incremental_dump():
    """ Get the latest incremental dump"""
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, dump_type
              FROM data_dump
             WHERE dump_type = 'incremental'
          ORDER BY id DESC
             LIMIT 1
        """))
        return result.mappings().first()


def get_previous_incremental_dump(dump_id):
    """ Get the id of the incremental dump that is one before the given dump id.

    Cannot just do dump_id - 1 because SERIAL/IDENTITY columns in postgres can skip values in some
    cases (for instance master/standby switchover).
    """
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT id, created, dump_type
              FROM data_dump
             WHERE id < :dump_id
               AND dump_type = 'incremental'
          ORDER BY id DESC
             LIMIT 1
        """), {"dump_id": dump_id})
        return result.mappings().first()
