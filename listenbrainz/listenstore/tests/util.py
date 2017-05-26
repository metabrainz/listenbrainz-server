# coding=utf-8

from datetime import datetime, timedelta
from listenbrainz.listen import Listen
import uuid


def generate_data(test_user_id, from_ts, num_records):
    test_data = []
    artist_msid = str(uuid.uuid4())

    for i in range(num_records):
        from_ts += 1   # Add one second
        item = Listen(user_id=test_user_id, timestamp=datetime.utcfromtimestamp(from_ts), artist_msid=artist_msid,
                      recording_msid=str(uuid.uuid4()))
        test_data.append(item)
    return test_data


def to_epoch(date):
    return int((date - datetime.utcfromtimestamp(0)).total_seconds())
