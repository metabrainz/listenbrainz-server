# coding=utf-8

import json
import os
import uuid

from datetime import datetime
from listenbrainz.listen import Listen


TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'testdata')


def generate_data(test_user_id, user_name, from_ts, num_records):
    test_data = []
    artist_msid = str(uuid.uuid4())

    if from_ts == None:  #check for playing now listens
        timestamp = None
    else:
        from_ts += 1   # Add one second
        timestamp = datetime.utcfromtimestamp(from_ts)

    for i in range(num_records):
        item = Listen(
            user_name=user_name,
            user_id=test_user_id,
            timestamp=timestamp,
            artist_msid=artist_msid,
            recording_msid=str(uuid.uuid4()),
            data={
                'artist_name': 'Frank Ocean',
                'track_name': 'Crack Rock',
                'additional_info': {},
            },
        )
        test_data.append(item)
    return test_data


def to_epoch(date):
    return int((date - datetime.utcfromtimestamp(0)).total_seconds())


def create_test_data_for_influxlistenstore(user_name):
    """Create listens for influxlistenstore tests.

    From a json file 'influx_listenstore_test_listens.json' in testdata
    it creates Listen objects with a specified user_name for tests.

    Args:
        user_name (str): MusicBrainz username of a user.

    Returns:
        A list of Listen objects.
    """
    test_data_file = os.path.join(TEST_DATA_PATH, 'influx_listenstore_test_listens.json')
    with open(test_data_file, 'r') as f:
        listens = json.load(f)

    test_data = []
    for listen in listens['payload']:
        listen['user_name'] = user_name
        test_data.append(Listen().from_json(listen))

    return test_data
