# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from datetime import datetime
import time
import sys
import os

from listen import Listen
import uuid
import pytz
import db.user


def generate_data(from_date, num_records):
    test_data = []
    current_date = to_epoch(from_date)
    artist_msid = str(uuid.uuid4())

    user = db.user.get_by_mb_id("test")
    if not user:
        db.user.create("test")
        user = db.user.get_by_mb_id("test")

    for i in range(num_records):
        current_date += 1   # Add one second
        item = Listen(user_id=user['id'], timestamp=datetime.utcfromtimestamp(current_date), artist_msid=artist_msid,
                      recording_msid=str(uuid.uuid4()))
        test_data.append(item)
    return test_data

def to_epoch(date):
    return int(time.mktime(date.timetuple()))
