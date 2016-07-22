# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from datetime import datetime, timedelta
from listenstore.listen import Listen
import uuid
import pytz

def generate_data(from_date, num_records):
    test_data = []
    current_date = to_epoch(from_date)
    artist_msid = str(uuid.uuid4())

    for i in range(num_records):
        current_date += 1   # Add one second
        item = Listen(user_id="test", timestamp=current_date, artist_msid=artist_msid,
                      recording_msid=str(uuid.uuid4()))
        test_data.append(item)
    return test_data


def to_epoch(date):
    return (date - pytz.utc.localize(datetime.utcfromtimestamp(0))).total_seconds()
