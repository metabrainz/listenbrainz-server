import listenbrainz_spark.stats.user.artist as user_artists
import listenbrainz_spark.stats.user.release as user_releases


def calculate():
    messages = []

    # Calculate artist stats
    messages = messages + user_artists.get_artists_week()
    messages = messages + user_artists.get_artists_month()
    messages = messages + user_artists.get_artists_year()
    messages = messages + user_artists.get_artists_all_time()

    # Calculate release stats
    messages = messages + user_releases.get_releases_week()
    messages = messages + user_releases.get_releases_month()
    messages = messages + user_releases.get_releases_year()
    messages = messages + user_releases.get_releases_all_time()

    return messages
