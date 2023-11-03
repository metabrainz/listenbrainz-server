import glob
import os.path
import time
from datetime import datetime

import orjson
import psycopg2
from psycopg2.extras import execute_values

from listenbrainz import messybrainz
from listenbrainz.db import timescale

pattern = "**/*.listens"
root_dir = "/data"


def get_files():
    def file_key(x):
        parts = x.split("/")
        year = int(parts[0])
        parts = parts[1].split(".")
        number = int(parts[0])
        return year, number

    files = glob.glob(pattern, root_dir=root_dir)
    files.sort(key=file_key)
    return files


def messybrainz_lookup(cursor, listens):
    msb_listens = []
    for listen in listens:
        artist = listen['track_metadata']['artist_name']
        recording = listen['track_metadata']['track_name']
        release = listen['track_metadata'].get('release_name')

        track_number = listen['track_metadata']['additional_info'].get('track_number')
        if track_number:
            track_number = str(track_number)

        duration = listen['track_metadata']['additional_info'].get('duration')
        if duration:
            duration = duration * 1000  # convert into ms
        else:  # try duration_ms field next
            duration_ms = listen['track_metadata']['additional_info'].get('duration_ms')
            if duration:
                duration = duration_ms

        key = f"{recording}-{artist}-{release}-{track_number}-{duration}"
        listen["key"] = key
        msb_listens.append((recording, artist, release, track_number, duration, key))

    query = """
        WITH intermediate AS (
            SELECT msb.gid::TEXT AS recording_msid
                 , t.key
                 , row_number() over (partition by msb.recording, msb.artist_credit, msb.release, msb.track_number, msb.duration ORDER BY msb.submitted) AS rnum
              FROM messybrainz.submissions msb
              JOIN (VALUES %s) AS t(recording, artist_credit, release, track_number, duration, key)
                ON lower(msb.recording) = lower(t.recording)
               AND lower(msb.artist_credit) = lower(t.artist_credit)
               AND ((lower(msb.release) = lower(t.release)) OR (msb.release IS NULL AND t.release IS NULL))
               AND ((lower(msb.track_number) = lower(t.track_number)) OR (msb.track_number IS NULL AND t.track_number IS NULL))
               AND ((msb.duration = t.duration) OR (msb.duration IS NULL AND t.duration IS NULL))
       ) 
            SELECT recording_msid
                 , key
              FROM intermediate
             WHERE rnum = 1
    """
    results = execute_values(cursor, query, msb_listens, template=None, fetch=True, page_size=1000)

    lookup_map = {}
    for row in results:
        lookup_map[row[1]] = row[0]

    for listen in listens:
        listen["recording_msid"] = lookup_map[listen["key"]]

    return listen


def process_file(cursor, file):
    print("======================================")
    print(f"Processing file {file}.")
    start = time.monotonic()

    file_read_start = time.monotonic()
    dumped_listens = []
    with open(os.path.join(root_dir, file)) as f:
        for line in f.readlines():
            temp = orjson.loads(line.strip())
            dumped_listens.append(temp)
    print(f"Listens: {len(dumped_listens)}")
    print(f"File Read: {time.monotonic() - file_read_start:%d} s")

    messybrainz_lookup_start = time.monotonic()
    listens = messybrainz_lookup(cursor, dumped_listens)
    print(f"MessyBrainz Lookup: {time.monotonic() - messybrainz_lookup_start:%d} s")

    prepare_listens_start = time.monotonic()
    listens_to_insert = [(
        datetime.fromtimestamp(l["timestamp"]),
        l["user_id"],
        l["recording_msid"],
        orjson.dumps(l["track_metadata"]).decode()
    )
        for l in listens
    ]
    print(f"Prepare listens: {time.monotonic() - prepare_listens_start:%d} s")

    insert_start = time.monotonic()
    query = """
        INSERT INTO listen_backup (listened_at, created, user_id, recording_msid, data)
             VALUES %s
        ON CONFLICT (listened_at, user_id, recording_msid)
          DO UPDATE 
                SET created = EXCLUDED.created
                  , data = EXCLUDED.data
    """
    execute_values(cursor, query, listens_to_insert, template="(%s, '2023-11-01 00:00:00+00', %s, %s, %s)")
    print(f"Insert: {time.monotonic() - insert_start:%d} s")

    print(f"Total time processing file {time.monotonic() - start:%d} s.")
    print("======================================")
    print()


def main():
    with timescale.engine.connect() as connection:
        raw_connection = connection.connection
        cursor = raw_connection.cursor()

        for file in get_files():
            process_file(cursor, file)
            connection.commit()
