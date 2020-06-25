#!/usr/bin/env python3

import os
import sys
import tarfile
from datetime import datetime

import ujson


def convert_comma_seperated_string_to_list(string):
    if not string:
        return []
    return [val for val in string.split(',')]


def convert_dump_row_to_spark_row(row):
    data = {
        'listened_at': str(row['timestamp']),
        'user_name': row['user_name'],
        'artist_msid': row['track_metadata']['additional_info']['artist_msid'],
        'artist_name': row['track_metadata']['artist_name'],
        'artist_mbids': convert_comma_seperated_string_to_list(row['track_metadata']['additional_info'].get('artist_mbids', '')),
        'release_msid': row['track_metadata']['additional_info'].get('release_msid'),
        'release_name': row['track_metadata'].get('release_name', ''),
        'release_mbid': row['track_metadata']['additional_info'].get('release_mbid', ''),
        'track_name': row['track_metadata']['track_name'],
        'recording_msid': row['recording_msid'],
        'recording_mbid': row['track_metadata']['additional_info'].get('recording_mbid', ''),
        'tags': convert_comma_seperated_string_to_list(row['track_metadata']['additional_info'].get('tags', [])),
    }

    if 'inserted_timestamp' in row and row['inserted_timestamp'] is not None:
        data['inserted_timestamp'] = str(datetime.utcfromtimestamp(row['inserted_timestamp']))
    else:
        data['inserted_timestamp'] = str(datetime.utcfromtimestamp(0))

    return data


def transmogrify(in_file, out_dir):


    with tarfile.open(in_file, "r:xz") as tarf:  # yep, going with that one again!
        for member in tarf:
            if member.name.endswith(".listens"):
                print(member.name)
                year = os.path.split(os.path.dirname(member.name))[1]
                file_name = os.path.split(member.name)[1]
                out_file = os.path.join(out_dir, year, file_name)
                try:
                    os.makedirs(os.path.join(out_dir, year))
                except FileExistsError: 
                    pass
                with open(out_file, "w") as out_f:
                    with tarf.extractfile(member) as f:
                        while True:
                            line = f.readline()
                            if not line:
                                break

                            listen = ujson.loads(line)
                            out_f.write(ujson.dumps(convert_dump_row_to_spark_row(listen)) + "\n")

transmogrify(sys.argv[1], sys.argv[2])
