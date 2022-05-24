import logging
import time

import sqlalchemy.exc

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import sqlalchemy
import psycopg2

from listenbrainz.messybrainz import exceptions, data

# This value must be incremented after schema changes on replicated tables!
SCHEMA_VERSION = 1

engine = None


def init_db_connection(connect_str):
    global engine
    while True:
        try:
            engine = create_engine(connect_str, poolclass=NullPool)
            break
        except psycopg2.OperationalError as e:
            print("Couldn't establish connection to db: {}".format(str(e)))
            print("Sleeping for 2 seconds and trying again...")
            time.sleep(2)


def run_sql_script(sql_file_path):
    with open(sql_file_path) as sql:
        connection = engine.connect()
        connection.execute(sql.read())
        connection.close()


def run_sql_script_without_transaction(sql_file_path):
    with open(sql_file_path) as sql:
        connection = engine.connect()
        connection.connection.set_isolation_level(0)
        lines = sql.read().splitlines()
        try:
            for line in lines:
                # TODO: Not a great way of removing comments. The alternative is to catch
                # the exception sqlalchemy.exc.ProgrammingError "can't execute an empty query"
                if line and not line.startswith("--"):
                    connection.execute(line)
        except sqlalchemy.exc.ProgrammingError as e:
            print("Error: {}".format(e))
            return False
        finally:
            connection.connection.set_isolation_level(1)
            connection.close()
        return True


def submit_listens_and_sing_me_a_sweet_song(recordings):
    """ Inserts a list of recordings into MessyBrainz.

    Args:
        recordings (list): a list of recordings to be inserted
    Returns:
        A dict with key 'payload' and value set to a list of dicts containing the recording data for each inserted recording
    """

    for r in recordings:
        if "artist" not in r or "title" not in r:
            raise exceptions.BadDataException("Require artist and title keys in submission")

    attempts = 0
    success = False
    while not success and attempts < 3:
        try:
            data = insert_all_in_transaction(recordings)
            success = True
        except sqlalchemy.exc.IntegrityError as e:
            # If we get an IntegrityError then our transaction failed.
            # We should try again
            pass

        attempts += 1

    if success:
        return {"payload": data}
    else:
        raise exceptions.ErrorAddingException("Failed to add data")


def load_recordings_from_msids(msids):
    """ Returns data for a recording with specified MessyBrainz ID.

    Args:
        msid (uuid): the MessyBrainz ID of the recording
    Returns:
        A dict containing the recording data for the recording with specified MessyBrainz ID
    """

    with engine.begin() as connection:
        return data.load_recordings_from_msids(connection, msids)


def insert_single(connection, recording):
    """ Inserts a single recording into MessyBrainz.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        recording: the recording to be inserted
    Returns:
        A dict containing the recording data for inserted recording
    """
    gid = data.get_id_from_recording(connection, recording)
    if not gid:
        gid = data.submit_recording(connection, recording)
    loaded = data.load_recordings_from_msids(connection, [gid])[0]
    return loaded


def insert_all_in_transaction(recordings):
    """ Inserts a list of recordings into MessyBrainz.

    Args:
        recordings (list): a list of recordings to be inserted
    Returns:
        A list of dicts containing the recording data for each inserted recording
    """

    ret = []
    with engine.begin() as connection:
        for recording in recordings:
            result = insert_single(connection, recording)
            ret.append(result)
    return ret
