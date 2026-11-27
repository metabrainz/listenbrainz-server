import unittest
from collections import namedtuple
from unittest import mock

from listenbrainz.webserver.views import donors as donors_views

User = namedtuple("User", ["id", "musicbrainz_id"])


class AddListenAndPlaylistCountsTestCase(unittest.TestCase):

    @mock.patch.object(donors_views.db_playlist, "get_playlist_count")
    @mock.patch.object(donors_views, "timescale_connection")
    def test_adds_counts_for_listenbrainz_users(self, mock_timescale_connection, mock_get_playlist_count):
        mock_timescale_connection._ts.get_listen_count_for_users.return_value = {1: 1234}
        mock_get_playlist_count.return_value = {1: 5}
        donors = [
            {"musicbrainz_id": "Foo", "is_listenbrainz_user": True},
            {"musicbrainz_id": "bar", "is_listenbrainz_user": True},
            {"musicbrainz_id": "not_on_listenbrainz", "is_listenbrainz_user": False},
        ]
        # get_many_users_by_mb_id returns users keyed by lowercased username
        donors_info = {"foo": User(1, "Foo"), "bar": User(2, "bar")}

        donors_views.add_listen_and_playlist_counts(donors, donors_info)

        mock_timescale_connection._ts.get_listen_count_for_users.assert_called_once_with([1, 2])
        self.assertEqual(mock_get_playlist_count.call_args[0][1], [1, 2])

        # "Foo" is matched to the lowercased key "foo"
        self.assertEqual(donors[0]["listenCount"], 1234)
        self.assertEqual(donors[0]["playlistCount"], 5)
        # a ListenBrainz user with no listens or playlists gets 0
        self.assertEqual(donors[1]["listenCount"], 0)
        self.assertEqual(donors[1]["playlistCount"], 0)
        # a donor who isn't a ListenBrainz user gets None
        self.assertIsNone(donors[2]["listenCount"])
        self.assertIsNone(donors[2]["playlistCount"])

    @mock.patch.object(donors_views.db_playlist, "get_playlist_count")
    @mock.patch.object(donors_views, "timescale_connection")
    def test_skips_queries_without_listenbrainz_users(self, mock_timescale_connection, mock_get_playlist_count):
        donors = [{"musicbrainz_id": "not_on_listenbrainz", "is_listenbrainz_user": False}]

        donors_views.add_listen_and_playlist_counts(donors, {})

        mock_timescale_connection._ts.get_listen_count_for_users.assert_not_called()
        mock_get_playlist_count.assert_not_called()
        self.assertIsNone(donors[0]["listenCount"])
        self.assertIsNone(donors[0]["playlistCount"])
