import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year


def get_listening_time(year):
    """ Calculate the total listening time in seconds of the user for the given year. """
    setup_listens_for_year(year)
    metadata_table = "recording_length"
    metadata_df = listenbrainz_spark.sql_context.read.parquet(config.HDFS_CLUSTER_URI + RECORDING_LENGTH_DATAFRAME)
    metadata_df.createOrReplaceTempView(metadata_table)

    data = run_query(_get_total_listening_time()).collect()
    yield {
        "type": "year_in_music_listening_time",
        "year": year,
        "data": data[0]["yearly_listening_time"]
    }


def _get_total_listening_time():
    # get recording length from recording table, if listen is unmapped default to 3 minutes.
    return """
          WITH listening_times AS (
                  SELECT user_id
                       , sum(COALESCE(rl.length / 1000, BIGINT(180))) AS total_listening_time
                    FROM listens_of_year l
               LEFT JOIN recording_length rl
                      ON l.recording_mbid = rl.recording_mbid
                GROUP BY user_id
          )
            SELECT to_json(
                    map_from_entries(
                        collect_list(
                            struct(user_id, total_listening_time)
                        )
                    )
                ) AS yearly_listening_time
          FROM listening_times  
    """
