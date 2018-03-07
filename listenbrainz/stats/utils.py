from listenbrainz.stats import STATS_QUEUE_REDIS_KEY_PREFIX

def construct_stats_queue_key(user_name):
    return '%s%s' % (STATS_QUEUE_REDIS_KEY_PREFIX, user_name)
