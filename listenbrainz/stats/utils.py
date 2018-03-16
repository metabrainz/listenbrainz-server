from listenbrainz.stats import STATS_QUEUE_REDIS_KEY_PREFIX

def construct_stats_queue_key(user_name):
    """ Returns the key that is used to check if user is in the stats queue.

    Args:
        user_name (str): the name of the user

    Returns:
        str: the key used to store if the user is in the stats queue
    """
    return '%s%s' % (STATS_QUEUE_REDIS_KEY_PREFIX, user_name)
