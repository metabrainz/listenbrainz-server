from listenbrainz_spark.stats.listener.entity import get_listener_stats
from listenbrainz_spark.stats.user.tests import StatsTestCase


class EntityListenerTestCase(StatsTestCase):

    def test_get_artists(self):
        messages = list(get_listener_stats("artists", "all_time"))
        self.assert_user_stats_equal(
            "user_top_artist_listeners_output.json",
            messages,
            "artists_listeners_all_time"
        )

    def test_get_release_groups(self):
        messages = list(get_listener_stats("release_groups", "all_time"))
        self.assert_user_stats_equal(
            "user_top_release_group_listeners_output.json",
            messages,
            "release_groups_listeners_all_time"
        )
