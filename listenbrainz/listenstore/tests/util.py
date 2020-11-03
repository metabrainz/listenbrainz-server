# coding=utf-8

import json
import os
import uuid

from datetime import datetime
from listenbrainz.listen import Listen


TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'testdata')


def generate_data(test_user_id, user_name, from_ts, num_records, inserted_ts=None):
    test_data = []
    artist_msid = str(uuid.uuid4())

    for i in range(num_records):
        if not inserted_ts:
            inserted_timestamp = datetime.utcnow()
        else:
            inserted_timestamp = datetime.utcfromtimestamp(inserted_ts)
        timestamp = datetime.utcfromtimestamp(from_ts)
        item = Listen(
            user_name=user_name,
            user_id=test_user_id,
            timestamp=timestamp,
            artist_msid=artist_msid,
            recording_msid=str(uuid.uuid4()),
            inserted_timestamp=inserted_timestamp,
            data={
                'artist_name': 'Frank Ocean',
                'track_name': 'Crack Rock',
                'additional_info': {},
            },
        )
        test_data.append(item)
        from_ts += 1   # Add one second
        if inserted_ts:
            inserted_ts += 1   # Add one second

    return test_data


def to_epoch(date):
    return int((date - datetime.utcfromtimestamp(0)).total_seconds())


def create_test_data_for_timescalelistenstore(user_name, test_data_file_name=None):
    """Create listens for timescalelistenstore tests.

    From a json file in testdata it creates Listen objects with a specified user_name for tests.

    Args:
        user_name (str): MusicBrainz username of a user.
        test_data_file_name (str): If specified use the given file to create Listen objects.
                                   DEFAULT = 'timescale_listenstore_test_listens.json'

    Returns:
        A list of Listen objects.
    """
    if not test_data_file_name:
        test_data_file_name = 'timescale_listenstore_test_listens.json'

    test_data_file = os.path.join(TEST_DATA_PATH, test_data_file_name)
    with open(test_data_file, 'r') as f:
        listens = json.load(f)

    test_data = []
    for listen in listens['payload']:
        listen['user_name'] = user_name
        test_data.append(Listen().from_json(listen))

    return test_data
