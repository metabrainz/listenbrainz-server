# coding=utf-8

from datetime import datetime, timezone
import time

from listenbrainz.listen import Listen
import uuid
import listenbrainz.db.user as db_user


def generate_data(db_conn, from_date, num_records, user_name):
    test_data = []
    current_date = int(time.mktime(from_date.timetuple()))

    user = db_user.get_or_create(db_conn, 1000, user_name)

    for i in range(num_records):
        current_date += 1   # Add one second
        item = Listen(
            user_id=user['id'],
            user_name=user_name,
            timestamp=datetime.fromtimestamp(current_date, timezone.utc),
            recording_msid=str(uuid.uuid4()),
            data={
                'artist_name': 'Test Artist Pls ignore',
                'track_name': 'Hello Goodbye',
                'additional_info': {},
            },
        )
        test_data.append(item)
    return test_data
