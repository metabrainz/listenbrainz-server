from listenbrainz_spark.stats import run_query

def prepare_user_data(table):
    """ Prepare users dataframe to select distinct user names and assign
        each user a unique integer id.

        Args:
            table (str): Registered dataframe to run SQL queries.

        Returns:
            users_df (dataframe): Columns can be depicted as:
                [
                    'user_id', 'user_name'
                ]
    """
    users_df = run_query("""
            SELECT user_name
                 , row_number() OVER (ORDER BY 'user_name') AS user_id
              FROM (SELECT DISTINCT user_name FROM %s)
        """ % (table))
    return users_df

def prepare_listen_data(table):
    """ Prepare listens dataframe to select all the listens from the
        registered dataframe.

        Args:
            table (str): Registered dataframe to run SQL queries.

        Returns:
            listens_df: Columns can be depicted as:
                [
                    'listened_at', 'track_name', 'recording_msid', 'user_name'
                ]
    """
    listens_df = run_query("""
            SELECT listened_at
                 , track_name
                 , recording_msid
                 , user_name
             FROM %s
        """ % (table))
    return listens_df

def prepare_recording_data(table):
    """ Prepare recordings dataframe to select distinct recordings/tracks
        listened to and assign each recording a unique integer id.

        Args:
            table (str): Registered dataframe to run SQL queries.

        Returns:
            recordings_df (dataframe): Columns can be depicted as:
                [
                    'track_name', 'recording_msid', 'artist_name', 'artist_msid',
                    'release_name', 'release_msid', 'recording_id'
                ]
    """
    recordings_df = run_query("""
            SELECT track_name
                 , recording_msid
                 , artist_name
                 , artist_msid
                 , release_name
                 , release_msid
                 , row_number() OVER (ORDER BY 'recording_msid') AS recording_id
              FROM (SELECT DISTINCT recording_msid, track_name, artist_name, artist_msid,
                    release_name, release_msid FROM %s)
        """ % (table))
    return recordings_df

def get_playcounts_data():
    """ Prepare playcounts dataframe by joining listens_df, users_df and
        recordings_df to select distinct tracks that a user has listened to
        for all the users along with listen count.

        Returns:
            playcounts_df (dataframe): Columns can be depicted as:
                [
                    'user_id', 'recording_id', 'count'
                ]
    """
    playcounts_df = run_query("""
        SELECT user_id,
               recording_id,
               count(recording_id) as count
          FROM listen
    INNER JOIN user
            ON listen.user_name = user.user_name
    INNER JOIN recording
            ON recording.recording_msid = listen.recording_msid
      GROUP BY user_id, recording_id
      ORDER BY user_id
    """)
    return playcounts_df
