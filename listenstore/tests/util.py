# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from datetime import timedelta
from listenstore.listen import Listen
import uuid


def generate_data(from_date, num_records):
    test_data = []
    current_date = from_date
    artist_msid = str(uuid.uuid4())

    for i in range(1, num_records):
        item = Listen(user_id="test", timestamp=current_date, artist_msid=artist_msid,
                      recording_msid=str(uuid.uuid4()))
        test_data.append(item)
        current_date += timedelta(seconds=1)
    return test_data
