import listenbrainz_spark.stats.user.entity as user_entity


def calculate():
    messages = []

    # Calculate artist stats
    messages = messages + user_entity.get_entity_week('artists')
    messages = messages + user_entity.get_entity_month('artists')
    messages = messages + user_entity.get_entity_year('artists')
    messages = messages + user_entity.get_entity_all_time('artists')

    # Calculate release stats
    messages = messages + user_entity.get_entity_week('releases')
    messages = messages + user_entity.get_entity_month('releases')
    messages = messages + user_entity.get_entity_year('releases')
    messages = messages + user_entity.get_entity_all_time('releases')

    return messages
