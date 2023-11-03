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


def messybrainz_lookup(listens):
    msb_listens = []
    for listen in listens:
        data = {
            'artist': listen['track_metadata']['artist_name'],
            'title': listen['track_metadata']['track_name'],
            'release': listen['track_metadata'].get('release_name'),
        }

        track_number = listen['track_metadata']['additional_info'].get('track_number')
        if track_number:
            data['track_number'] = str(track_number)

        duration = listen['track_metadata']['additional_info'].get('duration')
        if duration:
            data['duration'] = duration * 1000  # convert into ms
        else:  # try duration_ms field next
            duration_ms = listen['track_metadata']['additional_info'].get('duration_ms')
            if duration:
                data['duration'] = duration_ms

        msb_listens.append(data)

    msb_responses = messybrainz.submit_listens_and_sing_me_a_sweet_song(msb_listens)

    augmented_listens = []
    for listen, msid in zip(listens, msb_responses):
        listen['recording_msid'] = msid
        augmented_listens.append(listen)
    return augmented_listens


def process_file(cursor, file):
    print(f"Processing file {file}.", end=" ")
    start = time.monotonic()

    file_read_start = time.monotonic()
    dumped_listens = []
    with open(os.path.join(root_dir, file)) as f:
        for line in f.readlines():
            temp = orjson.loads(line.strip())
            dumped_listens.append(temp)
    print(f"Listens: {len(dumped_listens)}")
    print(f"File Read: {time.monotonic() - file_read_start} s")

    messybrainz_lookup_start = time.monotonic()
    listens = messybrainz_lookup(dumped_listens)
    listens_to_insert = [(
        datetime.fromtimestamp(l["timestamp"]),
        l["user_id"],
        l["recording_msid"],
        orjson.dumps(l["track_metadata"]).decode()
    )
        for l in listens
    ]
    print(f"MessyBrainz Lookup and dump json: {time.monotonic() - messybrainz_lookup_start} s")

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
    print(f"Insert: {time.monotonic() - insert_start} s")

    print(f"Took {time.monotonic() - start} s.")


def main():
    connection = timescale.engine.raw_connection()
    cursor = connection.cursor()

    for file in get_files():
        process_file(cursor, file)
        connection.commit()

    connection.close()
