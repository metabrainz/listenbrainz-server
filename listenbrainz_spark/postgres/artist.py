from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_artist_country_cache():
    """ Import artist country from postgres to HDFS for use in artist map stats calculation. """
    query = """
        SELECT a.gid AS artist_mbid
             , a.name AS artist_name
             , iso.code AS country_code
          FROM musicbrainz.artist a
          JOIN musicbrainz.area_containment ac
            ON ac.descendant = a.area
          JOIN musicbrainz.iso_3166_1 iso
            ON iso.area = ac.parent
    """

    save_pg_table_to_hdfs(query, ARTIST_COUNTRY_CODE_DATAFRAME)
