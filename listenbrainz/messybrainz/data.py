import json
import logging
import uuid

from hashlib import sha256
from listenbrainz.messybrainz import exceptions
from sqlalchemy import text


def get_id_from_meta_hash(connection, data):
    """ Gets Recording MessyBrainz ID from metadata.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        data: the recording data for which ID is to be returned

    Returns:
        The MessyBrainz ID for the recording with same metadata hash if it exists, None otherwise
    """

    meta = {"artist": data["artist"], "title": data["title"]}
    _, meta_json = convert_to_messybrainz_json(meta)
    meta_sha256 = sha256(meta_json.encode("utf-8")).hexdigest()

    query = text("""SELECT s.gid
                      FROM recording s
                 LEFT JOIN recording_json sj
                        ON sj.id = s.data
                     WHERE sj.meta_sha256 = :meta_sha256""")

    result = connection.execute(query, {"meta_sha256": meta_sha256})
    if result.rowcount:
        return result.fetchone()["gid"]
    else:
        return None


def get_artist_credit(connection, artist_credit):
    """ Returns the MessyBrainz artist ID for artist with specified artist credit

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        artist_credit (str): the name of the artist

    Returns:
        uuid (str): the Artist MessyBrainz ID if it exists, None otherwise
    """
    query = text("""SELECT a.gid
                      FROM artist_credit a
                     WHERE a.name = :name""")
    result = connection.execute(query, {"name": artist_credit})
    row = result.fetchone()
    if row:
        return str(row["gid"])
    return None


def get_release(connection, release):
    """ Returns the MessyBrainz release ID for release with specified release title.

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        release (str): the title of the release

    Returns:
        uuid(str): the Release MessyBrainz ID if it exists, None otherwise
    """

    query = text("""SELECT r.gid
                      FROM release r
                     WHERE r.title = :title""")
    result = connection.execute(query, {"title": release})
    row = result.fetchone()
    if row:
        return str(row["gid"])
    return None


def add_artist_credit(connection, artist_credit):
    """ Insert a new artist into the MessyBrainz database

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        artist_credit (str): the name of the artist

    Returns:
        uuid (str): the new Artist MessyBrainz ID
    """
    gid = str(uuid.uuid4())
    query = text("""INSERT INTO artist_credit (gid, name, submitted)
                         VALUES (:gid, :name, now())""")
    connection.execute(query, {"gid": gid, "name": artist_credit})
    return gid


def add_release(connection, release):
    """ Inserts a new release into the MessyBrainz database

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        release (str): the title of the release

    Returns:
        uuid (str): the new Release MessyBrainz ID
    """
    gid = str(uuid.uuid4())
    query = text("""INSERT INTO release (gid, title, submitted)
                         VALUES (:gid, :title, now())""")
    connection.execute(query, {"gid": gid, "title": release})
    return gid


def get_id_from_recording(connection, data):
    """ Returns the Recording MessyBrainz ID for recording with specified data

    Args:
        connection: the sqlalchemy db connection to be used to execute queries
        data (dict): the recording data dict submitted to MessyBrainz

    Returns:
        the MessyBrainz ID of the recording with passed data if it exists, None otherwise
    """
    _, data_json = convert_to_messybrainz_json(data)
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()

    query = text("""SELECT s.gid
                      FROM recording s
                 LEFT JOIN recording_json sj
                        ON sj.id = s.data
                     WHERE sj.data_sha256 = :data_sha256""")
    result = connection.execute(query, data_sha256=data_sha256)
    if result.rowcount:
        return result.fetchone()["gid"]
    else:
        return None


def submit_recording(connection, data):
    """ Submits a new recording to MessyBrainz.

    Args:
        connection: the sqlalchemy db connection to execute queries with
        data (dict): the recording data

    Returns:
        the Recording MessyBrainz ID of the data
    """
    data_json, sha256_json = convert_to_messybrainz_json(data)
    data_sha256 = sha256(sha256_json.encode("utf-8")).hexdigest()

    meta = {"artist": data["artist"], "title": data["title"]}
    meta_json, meta_sha256_json = convert_to_messybrainz_json(meta)
    meta_sha256 = sha256(meta_sha256_json.encode("utf-8")).hexdigest()

    artist = get_artist_credit(connection, data["artist"])
    if not artist:
        artist = add_artist_credit(connection, data["artist"])

    if "release" in data:
        release = get_release(connection, data["release"])
        if not release:
            release = add_release(connection, data["release"])
    else:
        release = None

    query = text("""INSERT INTO recording_json (data, data_sha256, meta_sha256)
                         VALUES (:data, :data_sha256, :meta_sha256)
                      RETURNING id""")
    result = connection.execute(query, {
        "data": data_json,
        "data_sha256": data_sha256,
        "meta_sha256": meta_sha256,
    })
    id = result.fetchone()["id"]
    gid = str(uuid.uuid4())
    query = text("""INSERT INTO recording (gid, data, artist, release, submitted)
                         VALUES (:gid, :data, :artist, :release, now())""")
    connection.execute(query, {
        "gid": gid,
        "data": id,
        "artist": artist,
        "release": release,
    })

    return gid


def load_recordings_from_msids(connection, messybrainz_ids):
    """ Returns data for a recordings corresponding to a given list of MessyBrainz IDs.
    msids not found in the database are omitted from the returned dict (usually indicates the msid
    is wrong because data is not deleted from MsB).

    Args:
        connection: sqlalchemy connection to execute db queries with
        messybrainz_ids (list [uuid]): the MessyBrainz IDs of the recordings to fetch data for

    Returns:
        list [dict]: a list of the recording data for the recordings in the order of the given MSIDs.
    """

    if not messybrainz_ids:
        return {}

    messybrainz_ids = [str(msid) for msid in messybrainz_ids]

    query = text("""SELECT DISTINCT rj.data
                         , r.artist
                         , r.release
                         , r.gid
                      FROM recording_json AS rj
                 LEFT JOIN recording AS r
                        ON rj.id = r.data
                     WHERE r.gid IN :msids""")
    result = connection.execute(query, msids=tuple(messybrainz_ids))

    rows = result.fetchall()
    if not rows:
        return []

    msid_recording_map = {str(x["gid"]): x for x in rows}

    # match results to every given mbid so list is returned in the same order
    results = []
    for msid in messybrainz_ids:
        if msid not in msid_recording_map:
            continue
        row = msid_recording_map[msid]
        results.append({
            "payload": row["data"],
            "ids": {
                "artist_msid": str(row["artist"]),
                "release_msid": str(row["release"]) if row["release"] else None,
                "recording_msid": str(row["gid"])
            }
        })

    return results


def convert_to_messybrainz_json(data):
    """ Converts the specified data dict into JSON strings, while
    applying MessyBrainz' transformations which include (if needed)
        * sorting by keys
        * lowercasing all values

    Args:
        data (dict): the dict to be converted into MessyBrainz JSON
    Returns:
        serialized (str): the MessyBrainz JSON with sorted keys
        serialized_lowercase(str): the MessyBrainz JSON with sorted keys and lowercase everything

    """
    serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return serialized, serialized.lower()
