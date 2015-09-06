from hashlib import sha256
import logging
import json
import db
import db.exceptions
import uuid

def get_id_from_scribble(data):
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()

    with db.create_cursor() as cursor:
        cursor.execute("""SELECT s.gid
                          FROM scribble s
                     LEFT JOIN scribble_json sj
                            ON sj.id = s.data
                        WHERE sj.data_sha256 = %s""", (data_sha256, ))

        if cursor.rowcount:
            return cursor.fetchone()["gid"]
        else:
            return None

def submit_scribble(data):
    data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
    data_sha256 = sha256(data_json.encode("utf-8")).hexdigest()

    with db._connection:
        with db.create_cursor() as cursor:
            cursor.execute("""INSERT INTO scribble_json (data, data_sha256)
                                VALUES (%s, %s)
                             RETURNING id""", (data_json, data_sha256))
            id = cursor.fetchone()["id"]
            gid = str(uuid.uuid4())
            cursor.execute("""INSERT INTO scribble (gid, data, submitted)
                                VALUES (%s, %s, now())""", (gid, id))

    return gid

def load_scribble(messybrainz_id):
    with db.create_cursor() as cursor:
        query = """SELECT sj.data
                        , r.musicbrainz_recording_id
                     FROM scribble_json sj
                LEFT JOIN scribble s
                       ON sj.id = s.data
                LEFT JOIN scribble_cluster sc
                       ON sc.gid = s.gid
                LEFT JOIN redirect r
                       ON r.cluster_id = sc.cluster_id
                    WHERE s.gid = %s"""
        cursor.execute(query, (str(messybrainz_id), ))
        if not cursor.rowcount:
            raise db.exceptions.NoDataFoundException
        row = cursor.fetchone()
        data = row["data"]
        recording_id = row["musicbrainz_recording_id"]
        data["musicbrainz_recording_id"] = recording_id
        return data

def link_scribble_to_recording_id(scribble_id, recording_id):
    with db.create_cursor() as cursor:
        cursor.execute("""INSERT INTO scribble_cluster (cluster_id, gid)
                               VALUES (%s, %s)""", (scribble_id, scribble_id))
        cursor.execute("""INSERT INTO redirect (cluster_id, musicbrainz_recording_id)
                               VALUES (%s, %s)""", (scribble_id, recording_id))

        db.commit()
