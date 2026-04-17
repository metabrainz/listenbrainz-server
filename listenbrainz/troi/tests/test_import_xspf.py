from unittest import TestCase
from unittest.mock import MagicMock, patch


SAMPLE_XSPF = """<?xml version="1.0" encoding="UTF-8"?>
<playlist version="1" xmlns="http://xspf.org/ns/0/">
  <title>Test Playlist</title>
  <trackList>
    <track><title>Blue</title><creator>Eiffel 65</creator></track>
  </trackList>
</playlist>"""


class TestImportFromXSPF(TestCase):

    @patch("listenbrainz.troi.import_ms.ImportXSPFPlaylistPatch")
    def test_import_from_xspf(self, MockPatch):
        """import_from_xspf must pass xspf_content and user token to the patch,
        run the pipeline, and return the JSPF with an identifier field."""
        mock_playlist = MagicMock()
        mock_playlist.get_jspf.return_value = {
            "playlist": {"title": "Test Playlist", "track": []}
        }
        mock_playlist.playlists = [MagicMock(mbid="some-playlist-mbid")]

        mock_patch_instance = MagicMock()
        mock_patch_instance.generate_playlist.return_value = mock_playlist
        MockPatch.return_value = mock_patch_instance

        from listenbrainz.troi.import_ms import import_from_xspf
        result = import_from_xspf(SAMPLE_XSPF, "user-token")

        # Patch must be constructed with the right args
        args_passed = MockPatch.call_args[0][0]
        assert args_passed["xspf_content"] == SAMPLE_XSPF
        assert args_passed["token"] == "user-token"

        # Result must be the JSPF dict with identifier added
        assert result["playlist"]["title"] == "Test Playlist"
        assert result["identifier"] == "some-playlist-mbid"
