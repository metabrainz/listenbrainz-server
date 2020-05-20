import listenbrainz_spark.stats.user.artist as user_artists


def calculate():
    messages = []

    messages = messages + user_artists.get_artists_week()
    messages = messages + user_artists.get_artists_month()
    messages = messages + user_artists.get_artists_year()
    messages = messages + user_artists.get_artists_all_time()

    return messages
