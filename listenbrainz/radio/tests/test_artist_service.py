from unittest.mock import patch, MagicMock
from troi import Recording, ArtistCredit, Artist
from troi.plist import plist

from listenbrainz.radio.artist import RecordingSearchByArtistService

SEED_MBID = "a74b1b7f-71a5-4011-9441-d0b5e4122711"
SIMILAR_MBID = "cb67438a-7f50-4f2b-a6f1-2bb2729fd538"

DB_ROW = {
    "recording_mbid": "401c1a5d-56e7-434d-b07e-a14d4e7eb83c",
    "similar_artist_mbid": SIMILAR_MBID,
    "similar_artist_name": "Test Artist",
    "total_listen_count": 12345,
}
DB_RETURN = {SIMILAR_MBID: [DB_ROW]}


class TestRecordingSearchByArtistService:

    def test_slug(self):
        assert RecordingSearchByArtistService().slug == "recording-search-by-artist"

    @patch("listenbrainz.radio.artist.lb_radio_artist", return_value=DB_RETURN)
    def test_easy_mode_divides_pop_by_100(self, mock_db):
        RecordingSearchByArtistService().search("easy", SEED_MBID, 0, 33, 35, 8)
        mock_db.assert_called_once_with("easy", SEED_MBID, 8, 35, 0.0, 0.33)

    @patch("listenbrainz.radio.artist.lb_radio_artist", return_value=DB_RETURN)
    def test_medium_mode_divides_pop_by_100(self, mock_db):
        RecordingSearchByArtistService().search("medium", SEED_MBID, 33, 66, 35, 8)
        mock_db.assert_called_once_with("medium", SEED_MBID, 8, 35, 0.33, 0.66)

    @patch("listenbrainz.radio.artist.lb_radio_artist", return_value=DB_RETURN)
    def test_hard_mode_divides_pop_by_100(self, mock_db):
        RecordingSearchByArtistService().search("hard", SEED_MBID, 66, 100, 35, 8)
        mock_db.assert_called_once_with("hard", SEED_MBID, 8, 35, 0.66, 1.0)

    @patch("listenbrainz.radio.artist.lb_radio_artist", return_value=DB_RETURN)
    def test_returns_recording_objects(self, mock_db):
        # Use pop_begin=0, pop_end=100 so random_item returns the item regardless of plist size.
        # (plist.random_item(0, 33, n) on a 1-item list returns [] because 33*1//100 == 0.)
        result, msgs = RecordingSearchByArtistService().search("easy", SEED_MBID, 0, 100, 1, 8)
        assert isinstance(result, dict)
        rec = result[SIMILAR_MBID]  # count=1 → random_item returns a single item, not a list
        assert isinstance(rec, Recording)
        assert rec.mbid == DB_ROW["recording_mbid"]
        assert rec.artist_credit.name == DB_ROW["similar_artist_name"]
        assert rec.musicbrainz["total_listen_count"] == DB_ROW["total_listen_count"]

    @patch("listenbrainz.radio.artist.lb_radio_artist", return_value={})
    def test_empty_db_result(self, mock_db):
        result, msgs = RecordingSearchByArtistService().search("easy", SEED_MBID, 0, 33, 35, 8)
        assert result == {}
        assert msgs == []

    @patch("listenbrainz.radio.artist.lb_radio_artist", return_value=DB_RETURN)
    def test_few_recordings_appends_msg(self, mock_db):
        # max_recordings_per_artist=100, but DB returns 1 row → 1 < 100-1=99 → msg appended
        _, msgs = RecordingSearchByArtistService().search("easy", SEED_MBID, 0, 33, 100, 8)
        assert len(msgs) == 1
        assert "Test Artist" in msgs[0]
        assert "easy" in msgs[0]

    @patch("listenbrainz.radio.artist.lb_radio_artist",
           return_value={SIMILAR_MBID: []})
    def test_empty_recordings_no_crash(self, mock_db):
        # Guard: len(recordings) == 0 must not try recordings[0]
        _, msgs = RecordingSearchByArtistService().search("easy", SEED_MBID, 0, 33, 35, 8)
        assert msgs == []
