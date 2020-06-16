import json
import os
from collections import defaultdict
from datetime import datetime

import listenbrainz_spark.stats.user.release as release_stats
from listenbrainz_spark import utils
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.tests import SparkTestCase
from pyspark.sql import Row


class releaseTestCase(SparkTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = LISTENBRAINZ_DATA_DIRECTORY

    def tearDown(self):
        path_found = utils.path_exists(self.path_)
        if path_found:
            utils.delete_dir(self.path_, recursive=True)

    def save_dataframe(self, filename):
        now = datetime.now()

        with open(self.path_to_data_file(filename)) as f:
            data = json.load(f)

        df = None
        for entry in data:
            for idx in range(0, entry['count']):
                # Assign listened_at to each listen
                row = utils.create_dataframe(Row(user_name=entry['user_name'], release_name=entry['release_name'],
                                                 release_msid=entry['release_msid'], release_mbid=entry['release_mbid'],
                                                 artist_name=entry['artist_name'], artist_msid=entry['artist_msid'],
                                                 artist_mbids=entry['artist_mbids']),
                                             schema=None)
                df = df.union(row) if df else row

        utils.save_parquet(df, os.path.join(self.path_, '{}/{}.parquet'.format(now.year, now.month)))

    def test_get_releases(self):
        self.save_dataframe('user_top_releases.json')
        df = utils.get_listens(datetime.now(), datetime.now(), self.path_)
        df.createOrReplaceTempView('test_view')

        expected = defaultdict(list)
        with open(self.path_to_data_file('user_top_releases.json')) as f:
            data = json.load(f)

        for entry in data:
            if entry['release_name'] != '':
                expected[entry['user_name']].append({
                    'release_name': entry['release_name'],
                    'release_msid': entry['release_msid'] or None,
                    'release_mbid': entry['release_mbid'] or None,
                    'artist_name': entry['artist_name'],
                    'artist_msid': entry['artist_msid'] or None,
                    'artist_mbids': entry['artist_mbids'],
                    'listen_count': entry['count']
                })

        # Sort in descending order w.r.t to listen_count
        for user_name, user_releases in expected.items():
            user_releases.sort(key=lambda release: release['listen_count'], reverse=True)

        data = release_stats.get_releases('test_view')
        received = defaultdict(list)
        for entry in data:
            _dict = entry.asDict(recursive=True)
            received[_dict['user_name']] = _dict['releases']

        self.assertDictEqual(received, expected)

    def test_get_releases_empty(self):
        self.save_dataframe('user_top_releases_empty.json')
        df = utils.get_listens(datetime.now(), datetime.now(), self.path_)
        df.createOrReplaceTempView('test_view')

        with open(self.path_to_data_file('user_top_releases.json')) as f:
            data = json.load(f)

        received = defaultdict(list)
        data = release_stats.get_releases('test_view')
        for entry in data:
            _dict = entry.asDict(recursive=True)
            received[_dict['user_name']] = _dict['releases']

        self.assertDictEqual(received, {})
