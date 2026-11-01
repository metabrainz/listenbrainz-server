"""
Tests for the per-MBID Redis cache inside fetch_metadata().

The cache lives in metadata_api.fetch_metadata so every caller
(lb-radio recording lookup, entity pages, /1/metadata/recording)
benefits automatically.
"""
from unittest.mock import patch, MagicMock

from listenbrainz.webserver.views.metadata_api import fetch_metadata

MBID_A = "aaaa-0001"
MBID_B = "bbbb-0002"

FULL_A = {
    "recording": {"name": "Creep"},
    "artist": {"name": "Radiohead"},
    "tag": {"recording": []},
    "release": {"name": "Pablo Honey"},
}
FULL_B = {
    "recording": {"name": "Karma Police"},
    "artist": {"name": "Radiohead"},
    "tag": {"recording": []},
    "release": {"name": "OK Computer"},
}


def _make_entry(mbid, full):
    entry = MagicMock()
    entry.recording_mbid = mbid
    entry.recording_data = full["recording"]
    entry.artist_data = full["artist"]
    entry.tag_data = full["tag"]
    entry.release_data = full["release"]
    return entry


class TestFetchMetadataCache:

    @patch("listenbrainz.webserver.views.metadata_api.cache")
    @patch("listenbrainz.webserver.views.metadata_api.get_metadata_for_recording")
    def test_cache_hit_skips_db(self, mock_db, mock_cache):
        mock_cache.get.return_value = FULL_A
        result = fetch_metadata([MBID_A], ["artist", "release"])
        mock_db.assert_not_called()
        assert result[MBID_A]["recording"] == FULL_A["recording"]
        assert result[MBID_A]["artist"] == FULL_A["artist"]

    @patch("listenbrainz.webserver.views.metadata_api.cache")
    @patch("listenbrainz.webserver.views.metadata_api.get_metadata_for_recording",
           return_value=[])
    def test_cache_miss_hits_db(self, mock_db, mock_cache):
        mock_cache.get.return_value = None
        fetch_metadata([MBID_A], ["artist"])
        mock_db.assert_called_once()

    @patch("listenbrainz.webserver.views.metadata_api.cache")
    @patch("listenbrainz.webserver.views.metadata_api.get_metadata_for_recording")
    def test_cache_miss_stores_full_data(self, mock_db, mock_cache):
        mock_cache.get.return_value = None
        mock_db.return_value = [_make_entry(MBID_A, FULL_A)]
        fetch_metadata([MBID_A], ["artist"])
        stored = mock_cache.set.call_args[0][1]
        assert "artist" in stored
        assert "tag" in stored
        assert "release" in stored

    @patch("listenbrainz.webserver.views.metadata_api.cache")
    @patch("listenbrainz.webserver.views.metadata_api.get_metadata_for_recording")
    def test_incs_filter_applied_on_cache_hit(self, mock_db, mock_cache):
        mock_cache.get.return_value = FULL_A
        result = fetch_metadata([MBID_A], ["artist"])
        assert "artist" in result[MBID_A]
        assert "tag" not in result[MBID_A]
        assert "release" not in result[MBID_A]

    @patch("listenbrainz.webserver.views.metadata_api.cache")
    @patch("listenbrainz.webserver.views.metadata_api.get_metadata_for_recording")
    def test_incs_filter_applied_on_cache_miss(self, mock_db, mock_cache):
        mock_cache.get.return_value = None
        mock_db.return_value = [_make_entry(MBID_A, FULL_A)]
        result = fetch_metadata([MBID_A], ["release"])
        assert "release" in result[MBID_A]
        assert "artist" not in result[MBID_A]
        assert "tag" not in result[MBID_A]

    @patch("listenbrainz.webserver.views.metadata_api.cache")
    @patch("listenbrainz.webserver.views.metadata_api.get_metadata_for_recording")
    def test_partial_hit_fetches_only_misses(self, mock_db, mock_cache):
        def _get(key, **kwargs):
            return FULL_A if MBID_A in key else None
        mock_cache.get.side_effect = _get
        mock_db.return_value = [_make_entry(MBID_B, FULL_B)]

        result = fetch_metadata([MBID_A, MBID_B], ["artist"])

        fetched = mock_db.call_args[0][1]
        assert MBID_A not in fetched
        assert MBID_B in fetched
        assert MBID_A in result
        assert MBID_B in result

    @patch("listenbrainz.webserver.views.metadata_api.cache")
    @patch("listenbrainz.webserver.views.metadata_api.get_metadata_for_recording")
    def test_cache_written_with_24h_ttl(self, mock_db, mock_cache):
        mock_cache.get.return_value = None
        mock_db.return_value = [_make_entry(MBID_A, FULL_A)]
        fetch_metadata([MBID_A], ["artist"])
        _key, _value, ttl = mock_cache.set.call_args[0]
        assert ttl == 86400
