from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_artist_country_cache():
    """ Import artist country from postgres to HDFS for use in artist map stats calculation. """
    query = """
        -- for the case where artist area is a subdivision of a country
        SELECT a.gid AS artist_mbid
             , a.name AS artist_name
             , iso.code AS country_code
          FROM musicbrainz.artist a
          JOIN musicbrainz.area_containment ac
            ON ac.descendant = a.area
          JOIN musicbrainz.iso_3166_1 iso
            ON iso.area = ac.parent
         UNION
         -- for the case where artist area is a country itself
        SELECT a.gid AS artist_mbid
             , a.name AS artist_name
             , iso.code AS country_code
          FROM musicbrainz.artist a
          JOIN musicbrainz.iso_3166_1 iso
            ON iso.area = a.area
        -- for the case where artist area is null
         UNION
        SELECT a.gid AS artist_mbid
             , a.name AS artist_name
             , NULL AS country_code
          FROM musicbrainz.artist a
         WHERE a.area IS NULL
    """

    save_pg_table_to_hdfs(query, ARTIST_COUNTRY_CODE_DATAFRAME)
