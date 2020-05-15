""" Calculate and return ALL user stats in rabbitmq compatible format
"""
from flask import current_app
import listenbrainz_spark.stats.user.artist as artist_stats
from collections import defaultdict


def calculate():
    # calculate and put artist stats into the result
    current_app.logger.debug("Running query...")
    artist_data = artist_stats.get_artists_last_year()
    messages = []
    for user_name, user_artists in artist_data.items():
        if (user_name == 'ishaanshah'):
            current_app.logger.debug(user_artists[:5])
        messages.append({
            'musicbrainz_id': user_name,
            'type': 'user_artist',
            'artist_stats': user_artists,
            'artist_count': len(user_artists),
        })
    current_app.logger.debug("Done!")

    return messages
