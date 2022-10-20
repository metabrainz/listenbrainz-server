# coding=utf-8

from datetime import datetime
import time
import sys
import os

from listenbrainz.listen import Listen
import uuid
import listenbrainz.db.user as db_user


def generate_data(from_date, num_records, user_name):
    test_data = []
    current_date = to_epoch(from_date)

    user = db_user.get_by_mb_id(user_name)
    if not user:
        db_user.create(user_name)
        user = db_user.get_by_mb_id(user_name)

    for i in range(num_records):
        current_date += 1   # Add one second
        item = Listen(
            user_id=user['id'],
            user_name=user_name,
            timestamp=datetime.utcfromtimestamp(current_date),
            recording_msid=str(uuid.uuid4()),
            data={
                'artist_name': 'Test Artist Pls ignore',
                'track_name': 'Hello Goodbye',
                'additional_info': {},
            },
        )
        test_data.append(item)
    return test_data

def to_epoch(date):
    return int(time.mktime(date.timetuple()))
