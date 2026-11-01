from unittest.mock import patch, MagicMock

from troi import Recording
from troi.patches.lb_radio_classes.recs import LBRadioRecommendationRecordingElement

from listenbrainz.radio.recs import LBRadioRecsService

USER_NAME = "recsuser"
USER_ID = 7
FAKE_USER = {"id": USER_ID}

REC_UNLISTENED_1 = {"recording_mbid": "aaaa-0001", "score": 9.5, "latest_listened_at": None}
REC_LISTENED_1   = {"recording_mbid": "bbbb-0002", "score": 8.0, "latest_listened_at": "2024-01-01"}
REC_UNLISTENED_2 = {"recording_mbid": "cccc-0003", "score": 7.0, "latest_listened_at": None}
REC_LISTENED_2   = {"recording_mbid": "dddd-0004", "score": 6.0, "latest_listened_at": "2024-06-01"}

ALL_RECS = [REC_UNLISTENED_1, REC_LISTENED_1, REC_UNLISTENED_2, REC_LISTENED_2]


def _make_db_recommendations(recs):
    recs_json = MagicMock()
    recs_json.dict.return_value = {"raw": recs}
    data = MagicMock()
    data.recording_mbid = recs_json
    return data


def _element_with_service(listened="all", mode="easy", db_recs=None):
    """Wire LBRadioRecsService into a Troi element backed by mocked DB data."""
    mock_patch = MagicMock()
    mock_patch.local_storage = {"data_cache": {"element-descriptions": []}}
    mock_patch.services = {"recs": LBRadioRecsService()}

    el = LBRadioRecommendationRecordingElement(USER_NAME, listened=listened, mode=mode)
    el.patch = mock_patch
    return el


class TestLBRadioRecsServiceFetch:

    def test_slug(self):
        assert LBRadioRecsService().slug == "recs"

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation")
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_returns_full_raw_list(self, _mock_user, mock_recs):
        mock_recs.return_value = _make_db_recommendations(ALL_RECS)
        result = LBRadioRecsService().fetch(USER_NAME)
        assert result == ALL_RECS

    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=None)
    def test_user_not_found_returns_none(self, _mock_user):
        assert LBRadioRecsService().fetch(USER_NAME) is None

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation",
           return_value=None)
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_no_recommendations_returns_none(self, _mock_user, _mock_recs):
        assert LBRadioRecsService().fetch(USER_NAME) is None

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation")
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_empty_raw_list_returns_empty(self, _mock_user, mock_recs):
        mock_recs.return_value = _make_db_recommendations([])
        assert LBRadioRecsService().fetch(USER_NAME) == []


class TestRecsElementWithService:
    """End-to-end: DB mock -> LBRadioRecsService -> Troi element -> returned Recordings."""

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation")
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_all_mode_returns_all_recordings(self, _mock_user, mock_recs):
        mock_recs.return_value = _make_db_recommendations(ALL_RECS)
        result = _element_with_service(listened="all").read([])
        mbids = {r.mbid for r in result}
        assert mbids == {r["recording_mbid"] for r in ALL_RECS}

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation")
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_unlistened_mode_returns_only_unlistened(self, _mock_user, mock_recs):
        mock_recs.return_value = _make_db_recommendations(ALL_RECS)
        result = _element_with_service(listened="unlistened").read([])
        mbids = {r.mbid for r in result}
        assert REC_UNLISTENED_1["recording_mbid"] in mbids
        assert REC_UNLISTENED_2["recording_mbid"] in mbids
        assert REC_LISTENED_1["recording_mbid"] not in mbids
        assert REC_LISTENED_2["recording_mbid"] not in mbids

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation")
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_listened_mode_returns_only_listened(self, _mock_user, mock_recs):
        mock_recs.return_value = _make_db_recommendations(ALL_RECS)
        result = _element_with_service(listened="listened").read([])
        mbids = {r.mbid for r in result}
        assert REC_LISTENED_1["recording_mbid"] in mbids
        assert REC_LISTENED_2["recording_mbid"] in mbids
        assert REC_UNLISTENED_1["recording_mbid"] not in mbids
        assert REC_UNLISTENED_2["recording_mbid"] not in mbids

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation")
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_medium_mode_skips_first_333_recommendations(self, _mock_user, mock_recs):
        # medium offset=333: only recs after index 333 should be considered
        padding = [{"recording_mbid": f"pad-{i:04d}", "score": 1.0, "latest_listened_at": None}
                   for i in range(400)]
        target_rec = {"recording_mbid": "target-0001", "score": 9.0, "latest_listened_at": None}
        mock_recs.return_value = _make_db_recommendations(padding + [target_rec])
        result = _element_with_service(listened="all", mode="medium").read([])
        mbids = {r.mbid for r in result}
        assert target_rec["recording_mbid"] in mbids
        assert "pad-0334" in mbids
        assert "pad-0000" not in mbids

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation")
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_no_recommendations_returns_empty(self, _mock_user, mock_recs):
        mock_recs.return_value = None
        result = _element_with_service(listened="all").read([])
        assert result == []

    @patch("listenbrainz.radio.recs.db_recommendations_cf_recording.get_user_recommendation")
    @patch("listenbrainz.radio.recs.db_user.get_by_mb_id", return_value=FAKE_USER)
    def test_returns_recording_objects(self, _mock_user, mock_recs):
        mock_recs.return_value = _make_db_recommendations([REC_UNLISTENED_1])
        result = _element_with_service(listened="all").read([])
        assert all(isinstance(r, Recording) for r in result)
        assert result[0].mbid == REC_UNLISTENED_1["recording_mbid"]
