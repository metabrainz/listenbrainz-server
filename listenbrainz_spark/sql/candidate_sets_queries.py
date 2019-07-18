from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query

from pyspark.sql.functions import lit

def get_top_artists(user_name):
    """ Prepare dataframe of top y (limit) artists listened to by the user where y
        is a config value.

        Args:
            user_name (str): User name of the user.

        Returns:
            top_artists_df (dataframe): Columns can be depicted as:
                [
                    'user_name', 'artist_name', 'artist_msid', 'count'
                ]
    """
    top_artists_df = run_query("""
            SELECT user_name
                 , artist_name
                 , artist_msid
                 , count(artist_msid) as count
              FROM listens_df
          GROUP BY user_name, artist_name, artist_msid
            HAVING user_name = "%s"
          ORDER BY count DESC
             LIMIT %s
    """ % (user_name, config.TOP_ARTISTS_LIMIT))
    return top_artists_df

def get_similar_artists_with_limit(artists):
    """ Prepare similar artists dataframe which consists of top x (limit) artists similar to each
        of the top artists listened to by the user where x is a config value.

        Args:
            artists (tuple): A tuple of top y artists names.

        Returns:
            similar_artists_df (dataframe): Columns can be depicted as:
                [
                    'artist_name', 'similar_artist_name'
                ]
    """
    similar_artists_df = run_query("""
        SELECT top_similar_artists.artist_name
             , top_similar_artists.similar_artist_name
          FROM (
            SELECT row_number() OVER (PARTITION BY similar_artists.artist_name ORDER BY similar_artists.count DESC)
                AS rank, similar_artists.*
              FROM (
                SELECT artist_name_0 as artist_name
                     , artist_name_1 as similar_artist_name
                     , count
                  FROM artists_relation
                 WHERE artist_name_0 IN %s
                 UNION
                SELECT artist_name_1 as artist_name
                     , artist_name_0 as similar_artist_name
                     , count
                  FROM artists_relation
                 WHERE artist_name_1 IN %s
              ) similar_artists
          ) top_similar_artists
         WHERE top_similar_artists.rank <= %s
    """ % (artists, artists, config.SIMILAR_ARTISTS_LIMIT))
    return similar_artists_df

def get_candidate_recording_ids(artists, user_id):
    """ Prepare dataframe of recording ids which belong to artists provided as argument.

        Args:
            artists (tuple): A tuple of artist names.
            user_id (int): User id of the user.

        Returns:
            candidate_recording_ids_df (dataframe): Columns can be depicted as:
                [
                    'user_id', 'recording_id'
                ]
    """
    df = run_query("""
        SELECT recording_id
          FROM recording
         WHERE artist_name IN %s
    """ % (artists,))
    candidate_recording_ids_df = df.withColumn('user_id', lit(user_id)).select('user_id', 'recording_id')
    return candidate_recording_ids_df

def get_net_similar_artists():
    """ Prepare dataframe consisting of similar artists which do not contain any of the
        top artists.

        Returns:
            net_similar_artists_df (dataframe): Column can be depicted as:
                [
                    'similar_artist_name'
                ]
    """
    net_similar_artists_df = run_query("""
        SELECT similar_artist_name
          FROM similar_artist
         WHERE similar_artist_name
        NOT IN (
            SELECT artist_name
              FROM top_artist
        )
    """)
    return net_similar_artists_df

def get_top_artists_with_collab():
    """ Prepare dataframe consisting of top artists with non zero collaborations.

        Returns:
            top_artists_with_collab_df (dataframe): Column can be depicted as:
                [
                    'artist_name'
                ]
    """
    top_artists_with_collab_df = run_query("""
        SELECT DISTINCT artist_name
          FROM similar_artist
    """)
    return top_artists_with_collab_df

def get_similar_artists_for_candidate_html(artist_name):
    """ Prepare dataframe consisting of artists similar to given artist.

        Args:
            artist_name (str): Artist name of top artist.

        Returns:
            df (dataframe): Column can be depicted as:
                [
                    'similar_artist_name'
                ]
    """
    df = run_query("""
        SELECT similar_artist_name
          FROM similar_artist
         WHERE artist_name = "%s"
    """ % (artist_name))
    return df
