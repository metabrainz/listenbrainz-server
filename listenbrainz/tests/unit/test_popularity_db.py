import unittest
from unittest.mock import patch, MagicMock

ARTIST_MBID = "b7ffd2af-418f-4be2-bdd1-22f8b48613da"
RECORDINGS = [{"recording_mbid": "abc", "total_listen_count": 100}]
RELEASE_GROUPS = [{"release_group_mbid": "def", "total_listen_count": 50}]


class TopRecordingsCacheTest(unittest.TestCase):

    @patch("listenbrainz.db.popularity.cache")
    def test_cache_hit_returns_data_without_db(self, mock_cache):
        mock_cache.get.return_value = RECORDINGS
        from listenbrainz.db.popularity import get_top_recordings_for_artist

        result = get_top_recordings_for_artist(MagicMock(), MagicMock(), ARTIST_MBID)

        self.assertEqual(result, RECORDINGS)
        mock_cache.get.assert_called_once_with(
            f"top_recordings.{ARTIST_MBID}.None", namespace="popularity", decode=True
        )
        mock_cache.set.assert_not_called()

    @patch("listenbrainz.db.popularity.cache")
    def test_empty_list_cache_hit_skips_db(self, mock_cache):
        """[] is a valid cached result -- artist with no popularity data."""
        mock_cache.get.return_value = []
        from listenbrainz.db.popularity import get_top_recordings_for_artist

        result = get_top_recordings_for_artist(MagicMock(), MagicMock(), ARTIST_MBID)

        self.assertEqual(result, [])
        mock_cache.set.assert_not_called()

    @patch("listenbrainz.db.popularity.color.fetch_color_for_releases")
    @patch("listenbrainz.db.popularity.load_recordings_from_mbids_with_redirects")
    @patch("listenbrainz.db.popularity.get_top_entity_for_artist")
    @patch("listenbrainz.db.popularity.psycopg2")
    @patch("listenbrainz.db.popularity.current_app", new=MagicMock())
    @patch("listenbrainz.db.popularity.cache")
    def test_cache_miss_runs_db_and_sets_cache(
        self, mock_cache, mock_psycopg2, mock_get_top, mock_load, mock_color
    ):
        mock_cache.get.return_value = None
        mock_get_top.return_value = []
        mock_load.return_value = []
        mock_color.return_value = {}
        mock_ts_conn = MagicMock()

        from listenbrainz.db.popularity import get_top_recordings_for_artist

        result = get_top_recordings_for_artist(MagicMock(), mock_ts_conn, ARTIST_MBID)

        self.assertEqual(result, [])
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once_with(
            f"top_recordings.{ARTIST_MBID}.None",
            [],
            86400,
            namespace="popularity",
            encode=True,
        )

    @patch("listenbrainz.db.popularity.cache")
    def test_count_produces_independent_cache_key(self, mock_cache):
        mock_cache.get.return_value = RECORDINGS
        from listenbrainz.db.popularity import get_top_recordings_for_artist

        get_top_recordings_for_artist(MagicMock(), MagicMock(), ARTIST_MBID, count=10)
        get_top_recordings_for_artist(MagicMock(), MagicMock(), ARTIST_MBID, count=None)

        keys = [c.args[0] for c in mock_cache.get.call_args_list]
        self.assertNotEqual(keys[0], keys[1])
        self.assertIn("top_recordings.%s.10" % ARTIST_MBID, keys[0])
        self.assertIn("top_recordings.%s.None" % ARTIST_MBID, keys[1])


class TopReleaseGroupsCacheTest(unittest.TestCase):

    @patch("listenbrainz.db.popularity.cache")
    def test_cache_hit_returns_data_without_db(self, mock_cache):
        mock_cache.get.return_value = RELEASE_GROUPS
        from listenbrainz.db.popularity import get_top_release_groups_for_artist

        result = get_top_release_groups_for_artist(MagicMock(), MagicMock(), ARTIST_MBID)

        self.assertEqual(result, RELEASE_GROUPS)
        mock_cache.get.assert_called_once_with(
            f"top_release_groups.{ARTIST_MBID}.None", namespace="popularity", decode=True
        )
        mock_cache.set.assert_not_called()

    @patch("listenbrainz.db.popularity.cache")
    def test_empty_list_cache_hit_skips_db(self, mock_cache):
        mock_cache.get.return_value = []
        from listenbrainz.db.popularity import get_top_release_groups_for_artist

        result = get_top_release_groups_for_artist(MagicMock(), MagicMock(), ARTIST_MBID)

        self.assertEqual(result, [])
        mock_cache.set.assert_not_called()

    @patch("listenbrainz.db.popularity.color.fetch_color_for_releases")
    @patch("listenbrainz.db.popularity.get_top_entity_for_artist")
    @patch("listenbrainz.db.popularity.cache")
    def test_cache_miss_runs_db_and_sets_cache(
        self, mock_cache, mock_get_top, mock_color
    ):
        mock_cache.get.return_value = None
        mock_get_top.return_value = []
        mock_color.return_value = {}

        from listenbrainz.db.popularity import get_top_release_groups_for_artist

        result = get_top_release_groups_for_artist(MagicMock(), MagicMock(), ARTIST_MBID)

        self.assertEqual(result, [])
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once_with(
            f"top_release_groups.{ARTIST_MBID}.None",
            [],
            86400,
            namespace="popularity",
            encode=True,
        )
