import json

from more_itertools import chunked

from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year

USERS_PER_MESSAGE = 5000


def get_listening_time(year):
    """ Calculate the total listening time in seconds of the user for the given year. """
    setup_listens_for_year(year)
    metadata_table = "recording_length"
    metadata_df = read_files_from_HDFS(RECORDING_LENGTH_DATAFRAME)
    metadata_df.createOrReplaceTempView(metadata_table)

    itr = run_query("""
          SELECT user_id
               , sum(COALESCE(rl.length / 1000, BIGINT(180))) AS value
            FROM listens_of_year l
       LEFT JOIN recording_length rl
              ON l.recording_mbid = rl.recording_mbid
        GROUP BY user_id
    """).toLocalIterator()

    for entry in chunked(itr, USERS_PER_MESSAGE):
        yield {
            "type": "year_in_music_listening_time",
            "year": year,
            "data": json.dumps({r.user_id: r.value for r in entry})
        }
