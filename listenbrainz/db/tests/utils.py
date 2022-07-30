import json
import os
from copy import deepcopy
from datetime import datetime

import requests

from listenbrainz.db import couchdb, stats
from listenbrainz.db.testing import TEST_DATA_PATH


def insert_test_stats(entity, range_, data_file):
    with open(os.path.join(TEST_DATA_PATH, data_file)) as f:
        original = json.load(f)

    # insert modifies the data in place so make a copy first
    data = deepcopy(original)

    database1, database2 = f"{entity}_{range_}_20220716", f"{entity}_{range_}_20220717"
    from_ts1, to_ts1 = int(datetime(2022, 7, 9).timestamp()), int(datetime(2022, 7, 16).timestamp())
    from_ts2, to_ts2 = int(datetime(2022, 7, 10).timestamp()), int(datetime(2022, 7, 17).timestamp())

    couchdb.create_database(database1)
    stats.insert(database1, from_ts1, to_ts1, data)

    couchdb.create_database(database2)
    stats.insert(database2, from_ts2, to_ts2, data[:1])
    return original, from_ts1, to_ts1, from_ts2, to_ts2


def delete_all_couch_databases():
    databases = couchdb.list_databases("")
    for database in databases:
        if database == "_users":
            continue
        databases_url = f"{couchdb.get_base_url()}/{database}"
        requests.delete(databases_url)
