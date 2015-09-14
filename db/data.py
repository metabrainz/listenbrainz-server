from hashlib import sha256
import logging
import json
import db
import db.exceptions
import uuid

def get_id_from_scribble(data):
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()

    query = """SELECT s.gid
                 FROM scribble s
            LEFT JOIN scribble_json sj
                   ON sj.id = s.data
                WHERE sj.data_sha256 = :data_sha256"""
    result = db.db.session.execute(query, {"data_sha256": data_sha256})
    if result.rowcount:
        return result.fetchone()["gid"]
    else:
        return None

def submit_scribble(data):
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()

    try:
        query = """INSERT INTO scribble_json (data, data_sha256)
                       VALUES (:data, :data_sha256)
                    RETURNING id"""
        result = db.db.session.execute(query, {"data": data_json,
                                            "data_sha256": data_sha256})
        id = result.fetchone()["id"]
        gid = str(uuid.uuid4())
        query = """INSERT INTO scribble (gid, data, submitted)
                        VALUES (:gid, :data, now())"""
        db.db.session.execute(query, {"gid": gid, "data": id})
        db.db.session.commit()
    except:
        db.db.session.rollback()
        raise

    return gid

def load_scribble(messybrainz_id):
    query = """SELECT sj.data
                    , r.musicbrainz_recording_id
                 FROM scribble_json sj
            LEFT JOIN scribble s
                   ON sj.id = s.data
            LEFT JOIN scribble_cluster sc
                   ON sc.gid = s.gid
            LEFT JOIN redirect r
                   ON r.cluster_id = sc.cluster_id
                WHERE s.gid = :gid"""
    result = db.db.session.execute(query, {"gid": str(messybrainz_id)})

    if not result.rowcount:
        raise db.exceptions.NoDataFoundException
    row = result.fetchone()
    data = row["data"]
    recording_id = row["musicbrainz_recording_id"]
    data["musicbrainz_recording_id"] = recording_id
    return data

def link_scribble_to_recording_id(scribble_id, recording_id):
    query = """INSERT INTO scribble_cluster (cluster_id, gid)
                    VALUES (:cluster_id, :gid)"""
    db.db.session.execute(query, {"cluster_id": scribble_id,
                               "gid": scribble_id})
    query = """INSERT INTO redirect (cluster_id, musicbrainz_recording_id)
                    VALUES (:cluster_id, :mbid)"""
    db.db.session.execute(query, {"cluster_id": scribble_id,
                               "mbid": recording_id})

