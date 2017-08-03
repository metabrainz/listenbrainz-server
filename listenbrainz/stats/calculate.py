import listenbrainz.stats.user as stats_user
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats


def calculate_user_stats():
    for user in get_recently_logged_in_users():
        recordings = stats_user.get_top_recordings(musicbrainz_id=user['musicbrainz_id'])
        artists    = stats_user.get_top_artists(musicbrainz_id=user['musicbrainz_id'])
        releases   = stats_user.get_top_releases(musicbrainz_id=user['musicbrainz_id'])

        db_stats.insert_user_stats(
            user_id=user['id'],
            artists=artists,
            recordings=recordings,
            releases=releases,
        )

def calculate_stats():
    calculate_user_stats()

