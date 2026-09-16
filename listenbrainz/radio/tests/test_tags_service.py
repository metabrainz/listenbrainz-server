from unittest.mock import patch
from troi import Recording
from troi.plist import plist

from listenbrainz.radio.tags import RecordingSearchByTagService

DB_ROWS = [
    {"recording_mbid": "401c1a5d-56e7-434d-b07e-a14d4e7eb83c", "percent": 75.0, "tag_count": 5, "source": "recording"},
    {"recording_mbid": "b0b40e78-b2b6-4ed9-b2c8-abcdef123456", "percent": 60.0, "tag_count": 3, "source": "release"},
]


class TestRecordingSearchByTagService:

    def test_slug(self):
        assert RecordingSearchByTagService().slug == "recording-search-by-tag"

    @patch("listenbrainz.radio.tags.db_tags.get_or", return_value=DB_ROWS)
    def test_or_easy_divides_pop_by_100(self, mock_get_or):
        RecordingSearchByTagService().search(["rock"], "OR", 0, 33, 10)
        mock_get_or.assert_called_once_with(["rock"], 0.0, 0.33, 10)

    @patch("listenbrainz.radio.tags.db_tags.get_or", return_value=DB_ROWS)
    def test_or_medium_divides_pop_by_100(self, mock_get_or):
        RecordingSearchByTagService().search(["rock"], "OR", 33, 66, 10)
        mock_get_or.assert_called_once_with(["rock"], 0.33, 0.66, 10)

    @patch("listenbrainz.radio.tags.db_tags.get_or", return_value=DB_ROWS)
    def test_or_hard_divides_pop_by_100(self, mock_get_or):
        RecordingSearchByTagService().search(["rock"], "OR", 66, 100, 10)
        mock_get_or.assert_called_once_with(["rock"], 0.66, 1.0, 10)

    @patch("listenbrainz.radio.tags.db_tags.get_and", return_value=DB_ROWS)
    def test_and_operator_calls_get_and(self, mock_get_and):
        RecordingSearchByTagService().search(["rock", "indie"], "AND", 0, 100, 5)
        mock_get_and.assert_called_once_with(["rock", "indie"], 0.0, 1.0, 5)

    @patch("listenbrainz.radio.tags.db_tags.get_or", return_value=DB_ROWS)
    def test_returns_plist_of_recordings(self, mock_get_or):
        result = RecordingSearchByTagService().search(["rock"], "OR", 0, 100, 10)
        assert isinstance(result, plist)
        assert len(result) == 2
        assert isinstance(result[0], Recording)
        assert result[0].mbid == DB_ROWS[0]["recording_mbid"]
        assert result[0].musicbrainz["popularity"] == DB_ROWS[0]["percent"]

    @patch("listenbrainz.radio.tags.db_tags.get_or", return_value=[])
    def test_empty_result_returns_empty_plist(self, mock_get_or):
        result = RecordingSearchByTagService().search(["nonexistent"], "OR", 0, 100, 10)
        assert isinstance(result, plist)
        assert len(result) == 0
