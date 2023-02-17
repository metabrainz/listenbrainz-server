from listenbrainz_spark.path import ARTIST_CREDIT_MBID_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_artist_credit_cache():
    """ Import artist country from postgres to HDFS for use in artist map stats calculation. """
    query = """
        SELECT ac.id AS artist_credit_id
             , ac.gid AS artist_credit_mbid
          FROM musicbrainz.artist_credit ac   
    """

    save_pg_table_to_hdfs(query, ARTIST_CREDIT_MBID_DATAFRAME)
