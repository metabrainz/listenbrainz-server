from messybrainz.db import exceptions
import sqlalchemy.exc
from messybrainz.db import data

from messybrainz import db

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


def load_recording_from_msid(msid):
    """ Returns data for a recording with specified MessyBrainz ID.

    Args:
        msid (uuid): the MessyBrainz ID of the recording
    Returns:
        A dict containing the recording data for the recording with specified MessyBrainz ID
    """

    with db.engine.begin() as connection:
        return data.load_recording_from_msid(connection, msid)


def load_recording_from_mbid(mbid):
    """ Returns data for a recording with specified MusicBrainz ID.

    Args:
        mbid (uuid): the MusicBrainz ID of the recording
    Returns:
        A dict containing the recording data for the recording with specified MusicBrainz ID
    """

    with db.engine.begin() as connection:
        return data.load_recording_from_mbid(connection, mbid)

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
    loaded = data.load_recording_from_msid(connection, gid)
    return loaded

def insert_all_in_transaction(recordings):
    """ Inserts a list of recordings into MessyBrainz.

    Args:
        recordings (list): a list of recordings to be inserted
    Returns:
        A list of dicts containing the recording data for each inserted recording
    """

    ret = []
    with db.engine.begin() as connection:
        for recording in recordings:
            result = insert_single(connection, recording)
            ret.append(result)
    return ret
