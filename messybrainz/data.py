from hashlib import sha256
import logging
import json
from messybrainz import exceptions
import uuid
from sqlalchemy.sql import text


def get_id_from_meta_hash(connection, data):
    meta = {"artist": data["artist"], "release": data["release"]}
    meta_json = json.dumps(meta, sort_keys=True, separators=(',', ':'))
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
    query = text("""SELECT a.gid
                 FROM artist_credit a
                WHERE a.name = :name""")
    result = connection.execute(query, {"name": artist_credit})
    row = result.fetchone()
    if row:
        return str(row["gid"])
    return None

def get_release(connection, release):
    query = text("""SELECT r.gid
                 FROM release r
                WHERE r.title = :title""")
    result = connection.execute(query, {"title": release})
    row = result.fetchone()
    if row:
        return str(row["gid"])
    return None

def add_artist_credit(connection, artist_credit):
    gid = str(uuid.uuid4())
    query = text("""INSERT INTO artist_credit (gid, name, submitted)
                    VALUES (:gid, :name, now())""")
    connection.execute(query, {"gid": gid, "name": artist_credit})
    return gid

def add_release(connection, release):
    gid = str(uuid.uuid4())
    query = text("""INSERT INTO release (gid, title, submitted)
                    VALUES (:gid, :title, now())""")
    connection.execute(query, {"gid": gid, "title": release})
    return gid

def get_id_from_recording(connection, data):
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
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
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()

    meta = {"artist": data["artist"], "title": data["title"]}
    meta_json = json.dumps(meta, sort_keys=True, separators=(',', ':'))
    meta_sha256 = sha256(meta_json.encode("utf-8")).hexdigest()

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
    result = connection.execute(query, {"data": data_json,
                                           "data_sha256": data_sha256,
                                           "meta_sha256": meta_sha256})
    id = result.fetchone()["id"]
    gid = str(uuid.uuid4())
    query = text("""INSERT INTO recording (gid, data, artist, release, submitted)
                    VALUES (:gid, :data, :artist, :release, now())""")
    connection.execute(query, {"gid": gid,
                                  "data": id,
                                  "artist": artist,
                                  "release": release})

    return gid

def load_recording(connection, messybrainz_id):
    query = text("""SELECT rj.data
                    , d.recording_mbid
                    , r.artist
                    , r.release
                    , r.gid
                 FROM recording_json rj
            LEFT JOIN recording r
                   ON rj.id = r.data
            LEFT JOIN recording_cluster rc
                   ON rc.recording_gid = r.gid
            LEFT JOIN recording_redirect d
                   ON d.recording_cluster_id = rc.cluster_id
                WHERE r.gid = :gid""")
    result = connection.execute(query, {"gid": str(messybrainz_id)})

    row = result.fetchone()
    if not row:
        raise exceptions.NoDataFoundException
    result = {}
    result["payload"] = row["data"]
    result["ids"] = {"recording_mbid": "", "artist_mbids": [], "release_mbid": ""}
    result["ids"]["artist_msid"] = str(row["artist"])
    result["ids"]["release_msid"] = str(row["release"]) if row["release"] else None
    result["ids"]["recording_msid"] = str(row["gid"])
    return result

def link_recording_to_recording_id(connection, msid, mbid):
    query = text("""INSERT INTO recording_cluster (cluster_id, gid)
                    VALUES (:cluster_id, :gid)""")
    connection.execute(query, {"cluster_id": msid,
                                  "gid": msid})
    query = text("""INSERT INTO recording_redirect (recording_cluster_id, recording_mbid)
                    VALUES (:cluster_id, :mbid)""")
    connection.execute(query, {"cluster_id": msid,
                                  "mbid": mbid})

