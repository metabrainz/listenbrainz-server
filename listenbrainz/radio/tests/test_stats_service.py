from unittest.mock import patch, MagicMock, call

from troi import Recording
from troi.patches.lb_radio_classes.stats import LBRadioStatsRecordingElement

from listenbrainz.radio.stats import LBRadioStatsService

USER_ID = 42
USER_NAME = "testuser"
TIME_RANGE = "month"

FAKE_USER = {"id": USER_ID, "musicbrainz_id": USER_NAME}

RECORDING_1 = {"recording_mbid": "aaaa-1111", "artist_mbids": ["bbbb-2222"]}
RECORDING_2 = {"recording_mbid": "cccc-3333", "artist_mbids": ["dddd-4444"]}


def _fake_stats():
    """Minimal stats object that mimics db_stats.get() return value."""
    r1 = MagicMock()
    r1.dict.return_value = RECORDING_1
    r2 = MagicMock()
    r2.dict.return_value = RECORDING_2

    stats = MagicMock()
    stats.data.__root__ = [r1, r2]
    return stats


class TestLBRadioStatsServiceFetch:

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=_fake_stats())
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_returns_recording_dicts(self, _mock_user, _mock_stats, mock_cache):
        mock_cache.get.return_value = None
        result = LBRadioStatsService().fetch(USER_NAME, TIME_RANGE, 0)
        assert len(result) == 2
        assert result[0]["recording_mbid"] == RECORDING_1["recording_mbid"]
        assert result[1]["recording_mbid"] == RECORDING_2["recording_mbid"]

    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=None)
    def test_raises_when_user_not_found(self, _mock_user):
        import pytest
        with pytest.raises(RuntimeError, match="Cannot find user"):
            LBRadioStatsService().fetch("nobody", TIME_RANGE, 0)

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=None)
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_raises_when_no_stats(self, _mock_user, _mock_stats, mock_cache):
        mock_cache.get.return_value = None
        import pytest
        with pytest.raises(RuntimeError, match="There are no stats available"):
            LBRadioStatsService().fetch(USER_NAME, TIME_RANGE, 0)


class TestLBRadioStatsServiceCache:

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=_fake_stats())
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_second_call_skips_couchdb(self, _mock_user, mock_stats, mock_cache):
        cached_result = [RECORDING_1, RECORDING_2]
        # First call: cache miss; second call: cache hit
        mock_cache.get.side_effect = [None, cached_result]

        svc = LBRadioStatsService()
        svc.fetch(USER_NAME, TIME_RANGE, 0)
        svc.fetch(USER_NAME, TIME_RANGE, 0)

        assert mock_stats.call_count == 1, "CouchDB should only be hit once across two identical fetches"

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=_fake_stats())
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_cache_written_with_one_hour_ttl(self, _mock_user, _mock_stats, mock_cache):
        mock_cache.get.return_value = None  # always miss

        LBRadioStatsService().fetch(USER_NAME, TIME_RANGE, 0)

        mock_cache.set.assert_called_once()
        _key, _value, ttl = mock_cache.set.call_args[0]
        assert ttl == 3600, f"Expected 1-hour TTL (3600s), got {ttl}"

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=None)
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_no_stats_result_is_not_cached(self, _mock_user, _mock_stats, mock_cache):
        mock_cache.get.return_value = None

        import pytest
        with pytest.raises(RuntimeError):
            LBRadioStatsService().fetch(USER_NAME, TIME_RANGE, 0)

        mock_cache.set.assert_not_called()

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=_fake_stats())
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_different_time_ranges_cached_independently(self, _mock_user, mock_stats, mock_cache):
        mock_cache.get.return_value = None  # always miss

        svc = LBRadioStatsService()
        svc.fetch(USER_NAME, "month", 0)
        svc.fetch(USER_NAME, "year", 0)

        assert mock_stats.call_count == 2, "Each time_range should produce a separate DB call"
        keys = [c[0][0] for c in mock_cache.set.call_args_list]
        assert keys[0] != keys[1], "month and year must produce different cache keys"

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=_fake_stats())
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_cache_key_encodes_user_and_time_range(self, _mock_user, _mock_stats, mock_cache):
        mock_cache.get.return_value = None

        LBRadioStatsService().fetch(USER_NAME, TIME_RANGE, 0)

        key = mock_cache.set.call_args[0][0]
        assert str(USER_ID) in key
        assert TIME_RANGE in key


class TestStatsElementWithService:
    """End-to-end: DB mock -> LBRadioStatsService -> Troi element -> returned Recordings."""

    def _element(self, mode="easy", time_range=TIME_RANGE):
        mock_patch = MagicMock()
        mock_patch.local_storage = {"data_cache": {"element-descriptions": []}}
        mock_patch.services = {"stats": LBRadioStatsService()}
        el = LBRadioStatsRecordingElement(USER_NAME, time_range, mode=mode)
        el.patch = mock_patch
        return el

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=_fake_stats())
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_element_uses_service_not_http(self, _mock_user, _mock_stats, mock_cache):
        mock_cache.get.return_value = None
        with patch("liblistenbrainz.ListenBrainz.get_user_recordings") as mock_http:
            self._element().read([])
            mock_http.assert_not_called()

    @patch("listenbrainz.radio.stats.cache")
    @patch("listenbrainz.radio.stats.db_stats.get", return_value=_fake_stats())
    @patch("listenbrainz.radio.stats.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_element_returns_recording_objects_with_artist_mbids(self, _mock_user, _mock_stats, mock_cache):
        mock_cache.get.return_value = None
        result = self._element().read([])
        assert all(isinstance(r, Recording) for r in result)
        mbids = {r.mbid for r in result}
        assert RECORDING_1["recording_mbid"] in mbids
        assert RECORDING_2["recording_mbid"] in mbids
        for r in result:
            assert r.artist_credit.musicbrainz["artist_mbids"] is not None

        key = mock_cache.set.call_args[0][0]
        assert str(USER_ID) in key
        assert TIME_RANGE in key
