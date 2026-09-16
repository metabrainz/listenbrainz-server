from unittest.mock import patch, MagicMock

from troi import Recording
from troi.musicbrainz.recording_lookup import RecordingLookupElement

from listenbrainz.radio.recording_lookup import RecordingLookupService

RECORDING_MBID = "401c1a5d-56e7-434d-b07e-a14d4e7eb83c"
ARTIST_MBID = "a74b1b7f-71a5-4011-9441-d0b5e4122711"

FAKE_DATA = {
    "recording": {"name": "Creep", "length": 238000},
    "artist": {
        "name": "Radiohead",
        "artist_credit_id": 5098,
        "artists": [{"artist_mbid": ARTIST_MBID, "name": "Radiohead", "join_phrase": ""}],
    },
    "release": {
        "name": "Pablo Honey",
        "mbid": "b5c5e8f0-7d6c-4a1e-9090-000000000001",
        "caa_id": 999,
        "caa_release_mbid": "b5c5e8f0-7d6c-4a1e-9090-000000000002",
        "release_group_mbid": "b5c5e8f0-7d6c-4a1e-9090-000000000003",
        "year": 1993,
    },
    "tag": {"artist": [], "release_group": [], "recording": []},
}


def _fake_fetch(recording_mbids, incs):
    if not recording_mbids:
        return {}
    data = {"recording": FAKE_DATA["recording"]}
    for key in ("artist", "tag", "release"):
        if key in incs:
            data[key] = FAKE_DATA[key]
    return {RECORDING_MBID: data}


class TestRecordingLookupService:

    def test_slug(self):
        assert RecordingLookupService().slug == "recording-lookup"

    @patch("listenbrainz.radio.recording_lookup.fetch_metadata", side_effect=_fake_fetch)
    def test_lookup_returns_keyed_by_mbid(self, mock_fetch):
        result = RecordingLookupService().lookup([RECORDING_MBID], "artist release")
        assert RECORDING_MBID in result

    @patch("listenbrainz.radio.recording_lookup.fetch_metadata", side_effect=_fake_fetch)
    def test_lookup_includes_artist_when_in_inc(self, mock_fetch):
        result = RecordingLookupService().lookup([RECORDING_MBID], "artist release")
        assert result[RECORDING_MBID]["artist"]["name"] == "Radiohead"

    @patch("listenbrainz.radio.recording_lookup.fetch_metadata", side_effect=_fake_fetch)
    def test_lookup_includes_release_when_in_inc(self, mock_fetch):
        result = RecordingLookupService().lookup([RECORDING_MBID], "artist release")
        assert result[RECORDING_MBID]["release"]["name"] == "Pablo Honey"

    @patch("listenbrainz.radio.recording_lookup.fetch_metadata", side_effect=_fake_fetch)
    def test_lookup_excludes_tag_when_not_in_inc(self, mock_fetch):
        result = RecordingLookupService().lookup([RECORDING_MBID], "artist release")
        assert "tag" not in result[RECORDING_MBID]

    @patch("listenbrainz.radio.recording_lookup.fetch_metadata", side_effect=_fake_fetch)
    def test_lookup_includes_tag_when_in_inc(self, mock_fetch):
        result = RecordingLookupService().lookup([RECORDING_MBID], "artist release tag")
        assert "tag" in result[RECORDING_MBID]

    @patch("listenbrainz.radio.recording_lookup.fetch_metadata", return_value={})
    def test_lookup_empty_returns_empty_dict(self, mock_fetch):
        result = RecordingLookupService().lookup([RECORDING_MBID], "artist release")
        assert result == {}

    @patch("listenbrainz.radio.recording_lookup.fetch_metadata", side_effect=_fake_fetch)
    def test_troi_uses_service_instead_of_http(self, mock_fetch):
        """Verify the Troi change: RecordingLookupElement uses our service when registered."""
        element = RecordingLookupElement()
        mock_patch = MagicMock()
        mock_patch.services = {"recording-lookup": RecordingLookupService()}
        element.patch = mock_patch

        recordings = [Recording(mbid=RECORDING_MBID)]
        with patch("troi.http_request.http_post") as mock_http:
            element.read([recordings])
            mock_http.assert_not_called()

    @patch("listenbrainz.radio.recording_lookup.fetch_metadata", side_effect=_fake_fetch)
    def test_troi_uses_service_sets_recording_name(self, mock_fetch):
        element = RecordingLookupElement()
        mock_patch = MagicMock()
        mock_patch.services = {"recording-lookup": RecordingLookupService()}
        element.patch = mock_patch

        rec = Recording(mbid=RECORDING_MBID)
        result = element.read([[rec]])
        assert result[0].name == "Creep"
        assert result[0].artist_credit.name == "Radiohead"
        assert result[0].release.name == "Pablo Honey"
        assert result[0].year == 1993
