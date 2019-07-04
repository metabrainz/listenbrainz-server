from listenbrainz_spark.stats import run_query

def get_user_id(user_name):
    """ Get user id using user name.

        Args:
            user_name: Name of the user.

        Returns:
            user_id: User id of the user.
    """
    result = run_query("""
        SELECT user_id
          FROM user
         WHERE user_name = '%s'
    """ % user_name)
    return result.first()['user_id']
