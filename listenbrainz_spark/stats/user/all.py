import itertools

import listenbrainz_spark.stats.user.entity as user_entity
import listenbrainz_spark.stats.user.listening_activity as user_listening_activity


def calculate():
    messages = itertools.chain()

    # Calculate artist stats
    messages = itertools.chain(messages, user_entity.get_entity_week('artists'))
    messages = itertools.chain(messages, user_entity.get_entity_month('artists'))
    messages = itertools.chain(messages, user_entity.get_entity_year('artists'))
    messages = itertools.chain(messages, user_entity.get_entity_all_time('artists'))

    # Calculate release stats
    messages = itertools.chain(messages, user_entity.get_entity_week('releases'))
    messages = itertools.chain(messages, user_entity.get_entity_month('releases'))
    messages = itertools.chain(messages, user_entity.get_entity_year('releases'))
    messages = itertools.chain(messages, user_entity.get_entity_all_time('releases'))

    # Calculate recording stats
    messages = itertools.chain(messages, user_entity.get_entity_week('recordings'))
    messages = itertools.chain(messages, user_entity.get_entity_month('recordings'))
    messages = itertools.chain(messages, user_entity.get_entity_year('recordings'))
    messages = itertools.chain(messages, user_entity.get_entity_all_time('recordings'))

    # Calculate listenig_activity stats
    messages = itertools.chain(messages, user_listening_activity.get_listening_activity_week())
    messages = itertools.chain(messages, user_listening_activity.get_listening_activity_month())
    messages = itertools.chain(messages, user_listening_activity.get_listening_activity_year())
    messages = itertools.chain(messages, user_listening_activity.get_listening_activity_all_time())

    return messages
