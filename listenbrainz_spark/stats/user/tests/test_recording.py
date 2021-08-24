import json
import os
from collections import defaultdict
from datetime import datetime

import listenbrainz_spark.stats.user.recording as recording_stats
from listenbrainz_spark import utils
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.tests import SparkTestCase
from pyspark.sql import Row
from pyspark.sql.types import (ArrayType, StringType, StructField,
                               StructType)


class RecordingTestCase(SparkTestCase):
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

        schema = StructType([
            StructField('artist_mbids', ArrayType(StringType())),
            StructField('artist_msid', StringType()),
            StructField('artist_name', StringType()),
            StructField('recording_mbid', StringType()),
            StructField('recording_msid', StringType()),
            StructField('release_mbid', StringType()),
            StructField('release_msid', StringType()),
            StructField('release_name', StringType()),
            StructField('track_name', StringType()),
            StructField('user_name', StringType()),
        ])
        df = None
        for entry in data:
            for idx in range(0, entry['count']):
                # Assign listened_at to each listen
                row = utils.create_dataframe(Row(
                    artist_mbids=entry['artist_mbids'],
                    artist_msid=entry['artist_msid'],
                    artist_name=entry['artist_name'],
                    recording_mbid=entry['recording_mbid'],
                    recording_msid=entry['recording_msid'],
                    release_mbid=entry['release_mbid'],
                    release_msid=entry['release_msid'],
                    release_name=entry['release_name'],
                    track_name=entry['track_name'],
                    user_name=entry['user_name'],
                ), schema=schema)
                df = df.union(row) if df else row

        utils.save_parquet(df, os.path.join(self.path_, '{}/{}.parquet'.format(now.year, now.month)))

    def test_get_recordings(self):
        self.save_dataframe('user_top_recordings.json')
        df = utils.get_listens(datetime.now(), datetime.now(), self.path_)
        df.createOrReplaceTempView('test_view')

        with open(self.path_to_data_file('user_top_recordings.json')) as f:
            data = json.load(f)

        with open(self.path_to_data_file('user_top_recordings_output.json')) as f:
            expected = json.load(f)

        data = recording_stats.get_recordings('test_view')
        received = defaultdict(list)
        for entry in data:
            _dict = entry.asDict(recursive=True)
            received[_dict['user_name']] = _dict['recordings']

        self.assertDictEqual(received, expected)
