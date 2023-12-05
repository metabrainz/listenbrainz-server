from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME, RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


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
          FROM musicbrainz.recording r
          JOIN musicbrainz.artist_credit_name acn
            ON acn.artist_credit = r.artist_credit
          JOIN musicbrainz.artist a
            ON a.id = acn.artist
      GROUP BY r.gid
    """

    save_pg_table_to_hdfs(query, RECORDING_ARTIST_DATAFRAME)
