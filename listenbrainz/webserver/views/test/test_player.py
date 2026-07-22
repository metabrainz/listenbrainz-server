import json
from unittest.mock import patch, MagicMock

from listenbrainz.tests.integration import IntegrationTestCase


class PlayerViewsTestCase(IntegrationTestCase):

    # ──────────────────────────────────────────────────
    #  POST /player/  (load_instant)
    # ──────────────────────────────────────────────────

    @patch("listenbrainz.webserver.views.player.fetch_playlist_recording_metadata")
    def test_load_instant_single_mbid(self, mock_fetch):
        """POST with a single valid recording MBID returns 200 and JSPF with one track."""
        mbid = "97e69767-5d34-4c97-b36a-f3b2b1ef9dae"
        resp = self.client.post(
            self.custom_url_for('player.load_instant', recording_mbids=mbid)
        )
        self.assert200(resp)
        data = json.loads(resp.data)

        # Top-level structure
        self.assertIn("playlist", data)
        playlist = data["playlist"]["playlist"]
        self.assertIn("title", playlist)
        self.assertIn("track", playlist)
        self.assertEqual(len(playlist["track"]), 1)

        # Track has the correct recording identifier
        track = playlist["track"][0]
        self.assertIn("identifier", track)
        self.assertIn(mbid, track["identifier"][0])

        mock_fetch.assert_called_once()

    @patch("listenbrainz.webserver.views.player.fetch_playlist_recording_metadata")
    def test_load_instant_multiple_mbids(self, mock_fetch):
        """POST with multiple comma-separated MBIDs returns a track for each."""
        mbids = "97e69767-5d34-4c97-b36a-f3b2b1ef9dae,a076e8af-5791-4531-a0ef-6b0a21f8e81c,cc197bad-dc9c-440d-a5b5-d52ba2e14234"
        resp = self.client.post(
            self.custom_url_for('player.load_instant', recording_mbids=mbids)
        )
        self.assert200(resp)
        data = json.loads(resp.data)
        tracks = data["playlist"]["playlist"]["track"]
        self.assertEqual(len(tracks), 3)

    @patch("listenbrainz.webserver.views.player.fetch_playlist_recording_metadata")
    def test_load_instant_custom_name_and_desc(self, mock_fetch):
        """Custom name and desc are reflected in the JSPF title and annotation."""
        mbid = "97e69767-5d34-4c97-b36a-f3b2b1ef9dae"
        resp = self.client.post(
            self.custom_url_for(
                'player.load_instant',
                recording_mbids=mbid,
                name="My Playlist",
                desc="A test description"
            )
        )
        self.assert200(resp)
        data = json.loads(resp.data)
        playlist = data["playlist"]["playlist"]
        self.assertEqual(playlist["title"], "My Playlist")
        self.assertEqual(playlist["annotation"], "A test description")

    @patch("listenbrainz.webserver.views.player.fetch_playlist_recording_metadata")
    def test_load_instant_default_name_and_desc(self, mock_fetch):
        """When name and desc are omitted, defaults to 'Instant playlist'."""
        mbid = "97e69767-5d34-4c97-b36a-f3b2b1ef9dae"
        resp = self.client.post(
            self.custom_url_for('player.load_instant', recording_mbids=mbid)
        )
        self.assert200(resp)
        data = json.loads(resp.data)
        playlist = data["playlist"]["playlist"]
        self.assertEqual(playlist["title"], "Instant playlist")
        self.assertEqual(playlist["annotation"], "Instant playlist")

    def test_load_instant_missing_recording_mbids(self):
        """POST without recording_mbids returns 400."""
        resp = self.client.post('/player/')
        self.assert400(resp)

    def test_load_instant_invalid_uuid(self):
        """POST with an invalid UUID returns 400."""
        resp = self.client.post(
            self.custom_url_for('player.load_instant', recording_mbids="not-a-valid-uuid")
        )
        self.assert400(resp)

    def test_load_instant_mixed_valid_invalid_uuids(self):
        """POST with one valid and one invalid UUID returns 400."""
        mbids = "97e69767-5d34-4c97-b36a-f3b2b1ef9dae,not-a-valid-uuid"
        resp = self.client.post(
            self.custom_url_for('player.load_instant', recording_mbids=mbids)
        )
        self.assert400(resp)

    # ──────────────────────────────────────────────────
    #  POST /player/release/<release_mbid>/  (load_release)
    # ──────────────────────────────────────────────────

    def test_load_release_invalid_uuid(self):
        """POST with an invalid release UUID returns 400."""
        resp = self.client.post('/player/release/not-a-valid-uuid/')
        self.assert400(resp)

    @patch("listenbrainz.webserver.views.player.mb_engine", new=True)
    @patch("listenbrainz.webserver.views.player.get_release_by_mbid")
    def test_load_release_not_found(self, mock_get_release):
        """POST with a valid UUID for a non-existent release returns 404."""
        mock_get_release.return_value = None
        resp = self.client.post('/player/release/9db51cd6-38f6-3b42-8ad5-559963d68f35/')
        self.assert404(resp)
        data = json.loads(resp.data)
        self.assertIn("error", data)

    @patch("listenbrainz.webserver.views.player.get_caa_ids_for_release_mbids")
    @patch("listenbrainz.webserver.views.player.psycopg2")
    @patch("listenbrainz.webserver.views.player.mb_engine", new=True)
    @patch("listenbrainz.webserver.views.player.get_release_by_mbid")
    def test_load_release_valid(self, mock_get_release, mock_psycopg2, mock_get_caa):
        """POST with a valid release MBID returns 200 and JSPF with tracks."""
        release_mbid = "9db51cd6-38f6-3b42-8ad5-559963d68f35"

        mock_get_release.return_value = {
            "name": "OK Computer",
            "mbid": release_mbid,
            "artist-credit-phrase": "Radiohead",
            "medium-list": [
                {
                    "track-list": [
                        {
                            "name": "Airbag",
                            "position": 1,
                            "recording_id": "b1d58a57-a0f3-4b20-aab0-d7afd3a58f09",
                            "artist-credit-phrase": "Radiohead",
                            "artist-credit": [
                                {"artist": {"mbid": "a74b1b7f-71a5-4011-9441-d0b5e4122711"}}
                            ],
                        },
                        {
                            "name": "Paranoid Android",
                            "position": 2,
                            "recording_id": "e3cb1e21-8e24-4809-9f9e-2c79a6e6bdb0",
                            "artist-credit-phrase": "Radiohead",
                            "artist-credit": [
                                {"artist": {"mbid": "a74b1b7f-71a5-4011-9441-d0b5e4122711"}}
                            ],
                        },
                    ]
                }
            ],
        }

        # Mock psycopg2 connection + cursor context managers
        mock_curs = MagicMock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_curs)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_psycopg2.connect.return_value = mock_conn
        mock_psycopg2.extras = MagicMock()

        mock_get_caa.return_value = {
            release_mbid: {"caa_id": 12345, "caa_release_mbid": release_mbid}
        }

        resp = self.client.post(f'/player/release/{release_mbid}/')
        self.assert200(resp)
        data = json.loads(resp.data)

        playlist = data["playlist"]["playlist"]
        self.assertEqual(len(playlist["track"]), 2)
        self.assertEqual(playlist["track"][0]["title"], "Airbag")
        self.assertEqual(playlist["track"][0]["creator"], "Radiohead")
        self.assertEqual(playlist["track"][1]["title"], "Paranoid Android")

    @patch("listenbrainz.webserver.views.player.mb_engine", new=None)
    def test_load_release_no_mb_engine(self):
        """When mb_engine is None, returns 200 with an empty playlist."""
        resp = self.client.post('/player/release/9db51cd6-38f6-3b42-8ad5-559963d68f35/')
        self.assert200(resp)
        data = json.loads(resp.data)
        self.assertEqual(data["playlist"], {})

    # ──────────────────────────────────────────────────
    #  GET /player/  (index — serves React SPA)
    # ──────────────────────────────────────────────────

    def test_player_index_get(self):
        """GET /player/ serves the React SPA page (index.html)."""
        resp = self.client.get('/player/')
        self.assert200(resp)
