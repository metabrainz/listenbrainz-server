""" Calculate and return ALL user stats in rabbitmq compatible format
"""
from flask import current_app
import listenbrainz_spark.stats.user.artist as artist_stats


def calculate():
    # calculate and put artist stats into the result
    current_app.logger.debug("Running query...")
    messages = []

    current_app.logger.debug("Calculating artist_all_time...")
    artist_data = artist_stats.get_artists_all_time()
    for user_name, user_artists in artist_data.items():
        messages.append({
            'musicbrainz_id': user_name,
            'type': 'user_artists',
            'range': 'all_time',
            'artists': user_artists,
            'count': len(user_artists)
        })

    current_app.logger.debug("Calculating artist_last_year...")
    artist_data = artist_stats.get_artists_last_year()
    for user_name, user_artists in artist_data.items():
        messages.append({
            'musicbrainz_id': user_name,
            'type': 'user_artists',
            'range': 'last_year',
            'artists': user_artists,
            'count': len(user_artists)
        })

    current_app.logger.debug("Calculating artist_last_month...")
    artist_data = artist_stats.get_artists_last_month()
    for user_name, user_artists in artist_data.items():
        messages.append({
            'musicbrainz_id': user_name,
            'type': 'user_artists',
            'range': 'last_month',
            'artists': user_artists,
            'count': len(user_artists)
        })

    current_app.logger.debug("Calculating artist_last_week...")
    artist_data = artist_stats.get_artists_last_week()
    for user_name, user_artists in artist_data.items():
        messages.append({
            'musicbrainz_id': user_name,
            'type': 'user_artists',
            'range': 'last_week',
            'artists': user_artists,
            'count': len(user_artists)
        })

    current_app.logger.debug("Done!")

    return messages
