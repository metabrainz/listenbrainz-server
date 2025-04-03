from typing import Optional

from pyspark import StorageLevel
from pyspark.sql import DataFrame

from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME, RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs
from listenbrainz_spark.utils import read_files_from_HDFS

_RECORDING_ARTIST_CACHE = "recording_artist_cache"
_recording_artist_df: Optional[DataFrame] = None


def create_recording_length_cache():
    """ Import recording lengths from postgres to HDFS for use in year in music and similar entity calculation. """
    query = """
        SELECT r.gid AS recording_mbid
             , r.length
          FROM musicbrainz.recording r   
    """

    save_pg_table_to_hdfs(query, RECORDING_LENGTH_DATAFRAME)


def create_recording_artist_cache():
    """ Import recording artists from postgres to HDFS for use in periodic jams calculation. """
    query = """
        SELECT r.gid AS recording_mbid
             , array_agg(a.gid ORDER BY acn.position) AS artist_mbids
             , jsonb_agg(
                    jsonb_build_object(
                        'artist_credit_name', acn.name,
                        'join_phrase', acn.join_phrase,
                        'artist_mbid', a.gid::TEXT
                    )
                    ORDER BY acn.position
               ) AS artists
          FROM musicbrainz.recording r
          JOIN musicbrainz.artist_credit_name acn
            ON acn.artist_credit = r.artist_credit
          JOIN musicbrainz.artist a
            ON a.id = acn.artist
      GROUP BY r.gid
    """

    save_pg_table_to_hdfs(query, RECORDING_ARTIST_DATAFRAME, process_artists_column=True)

    unpersist_recording_artist_cache()


def get_recording_artist_cache():
    """ Read the RECORDING_ARTIST_CACHE parquet files from HDFS and create a spark SQL view
     if one already doesn't exist """
    global _recording_artist_df
    if _recording_artist_df is None:
        _recording_artist_df = read_files_from_HDFS(RECORDING_ARTIST_DATAFRAME)
        _recording_artist_df.persist(StorageLevel.DISK_ONLY)
        _recording_artist_df.createOrReplaceTempView(_RECORDING_ARTIST_CACHE)
    return _RECORDING_ARTIST_CACHE


def unpersist_recording_artist_cache():
    global _recording_artist_df
    if _recording_artist_df is not None:
        _recording_artist_df.unpersist()
        _recording_artist_df = None
