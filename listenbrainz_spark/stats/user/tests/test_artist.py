import json
import os
from collections import defaultdict
from datetime import datetime

import listenbrainz_spark.stats.user.artist as artist_stats
from listenbrainz_spark import utils
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (adjust_days, adjust_months, replace_days,
                                      replace_months)
from listenbrainz_spark.stats.user.utils import get_last_monday
from listenbrainz_spark.tests import SparkTestCase
from pyspark.sql import Row, catalog

TEST_DATA_PATH = '../../../testdata'


class ArtistTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = LISTENBRAINZ_DATA_DIRECTORY

    def tearDown(self):
        path_found = utils.path_exists(self.path_)
        if path_found:
            utils.delete_dir(self.path_, recursive=True)

    def save_dataframe(self):
        now = datetime.now()
        days = []
        # Date in all_time
        days.append(adjust_months(now, 13))
        # Date in year
        days.append(replace_months(now, 1))
        # Date in month
        days.append(replace_days(now, 1))
        # Date in week
        days.append(adjust_days(get_last_monday(now), 3))

        with open(self.path_to_data_file('user_top_artists.json')) as f:
            data = json.load(f)

        df = None
        for entry in data:
            for idx in range(0, entry['count']):
                # Assign listened_at to each listen
                row = utils.create_dataframe(Row(user_name=entry['user_name'], artist_name=entry['artist_name'],
                                                 artist_msid=entry['artist_msid'], artist_mbids=entry['artist_mbids'],
                                                 listened_at=days[idx % 4]), schema=None)
                df = df.union(row) if df else row

        utils.save_parquet(df, os.path.join(self.path_, '{}/{}.parquet'.format(now.year, now.month)))

    def test_get_artist(self):
        self.save_dataframe()
        df = utils.get_listens(datetime.now(), datetime.now(), self.path_)
        df.createOrReplaceTempView('test_view')

        expected = defaultdict(list)
        with open(self.path_to_data_file('user_top_artists.json')) as f:
            data = json.load(f)

        for entry in data:
            expected[entry['user_name']].append({
                'artist_name': entry['artist_name'],
                'artist_msid': entry['artist_msid'],
                'artist_mbids': entry['artist_mbids'],
                'listen_count': entry['count']
            })

        # Sort in descending order w.r.t to listen_count
        for user_name, user_artists in expected.items():
            user_artists.sort(key=lambda artist: artist['listen_count'], reverse=True)

        received = artist_stats.get_artists('test_view')

        self.assertDictEqual(received, expected)
        catalog.deleteTempView('test_view')

    def test_get_artist_week(self):
        self.save_dataframe()

        now = datetime.now()
        to_ts = get_last_monday(now).timestamp()
        from_ts = adjust_days(get_last_monday(now), 7).timestamp()
        expected = [
            {
                'musicbrainz_id': 'user1',
                'type': 'user_artists',
                'range': 'last_week',
                'from': from_ts,
                'to': to_ts,
                'artists': [
                ],
                'count': 4
            }
        ]

        received = artist_stats.get_artists_last_week()
