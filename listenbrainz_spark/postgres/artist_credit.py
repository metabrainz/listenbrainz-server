from listenbrainz_spark.path import ARTIST_CREDIT_MBID_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_artist_credit_cache():
    """ Import artist country from postgres to HDFS for use in artist map stats calculation. """
    query = """
        SELECT ac.id AS artist_credit_id
             , a.gid AS artist_mbid
             , acn.position
             , acn.join_phrase
          FROM musicbrainz.artist_credit ac
          JOIN musicbrainz.artist_credit_name acn
            ON acn.artist_credit = ac.id
          JOIN musicbrainz.artist a
            ON acn.artist = a.id 
    """

    save_pg_table_to_hdfs(query, ARTIST_CREDIT_MBID_DATAFRAME)
