from listenbrainz_spark.stats.user.listening_activity import get_listening_activity


def calculate_listens_per_day():
    return get_listening_activity("year_in_music", "year_in_music_listens_per_day")
