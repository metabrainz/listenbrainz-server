from messybrainz.db import exceptions
import sqlalchemy.exc
from messybrainz.db import data

from messybrainz import db

def submit_listens_and_sing_me_a_sweet_song(recordings):

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

def load_recording(mbid):
    with db.engine.begin() as connection:
        return data.load_recording(connection, mbid)


def insert_single(connection, recording):
    gid = data.get_id_from_recording(connection, recording)
    if not gid:
        gid = data.submit_recording(connection, recording)
    loaded = data.load_recording(connection, gid)
    return loaded

def insert_all_in_transaction(recordings):
    ret = []
    with db.engine.begin() as connection:
        for recording in recordings:
            result = insert_single(connection, recording)
            ret.append(result)
    return ret
