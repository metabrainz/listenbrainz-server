import io
from unittest.mock import patch, MagicMock

from PIL import Image

from listenbrainz.art.og_image import (
    generate_playlist_og_image,
    _compose_single,
    _compose_grid_2x2,
    _download_image,
    OPENGRAPH_IMAGE_WIDTH,
    OPENGRAPH_IMAGE_HEIGHT,
    GRID_WIDTH,
    _MAX_DOWNLOAD_SIZE,
)
from listenbrainz.tests.integration import IntegrationTestCase


def _create_dummy_png(width=500, height=500, color=(255, 0, 0, 255)):
    """Create a small dummy PNG image in memory for testing."""
    img = Image.new("RGBA", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


class TestComposeHelpers:

    def test_compose_single_creates_correct_size(self):
        cover = Image.new("RGBA", (500, 500), (255, 0, 0, 255))
        result = _compose_single(cover)
        assert result.size == (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT)

    def test_compose_grid_2x2_creates_correct_size(self):
        covers = [Image.new("RGBA", (500, 500), (i * 50, 0, 0, 255)) for i in range(4)]
        result = _compose_grid_2x2(covers)
        assert result.size == (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT)

    def test_compose_grid_2x2_places_all_four_images(self):
        """Each tile region should contain the colour we painted it, not black (background bleed)."""
        colors = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255)]
        covers = [Image.new("RGBA", (500, 500), c) for c in colors]
        result = _compose_grid_2x2(covers)

        tile_w = GRID_WIDTH // 2
        tile_h = OPENGRAPH_IMAGE_HEIGHT // 2

        # sample a pixel from the centre of each tile — if the grid
        # placed covers correctly, it should match the input colour
        positions = [
            (tile_w // 2, tile_h // 2),                     # top-left
            (tile_w + tile_w // 2, tile_h // 2),             # top-right
            (tile_w // 2, tile_h + tile_h // 2),             # bottom-left
            (tile_w + tile_w // 2, tile_h + tile_h // 2),    # bottom-right
        ]

        for (x, y), expected_color in zip(positions, colors):
            pixel = result.getpixel((x, y))
            assert pixel == expected_color, f"Pixel at ({x}, {y}) was {pixel}, expected {expected_color}"


class TestDownloadImage:

    @patch("listenbrainz.art.og_image.req.get")
    def test_download_image_success(self, mock_get):
        dummy_png = _create_dummy_png()
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.iter_content.return_value = [dummy_png]
        mock_response.raise_for_status = MagicMock()
        mock_response.close = MagicMock()
        mock_get.return_value = mock_response

        result = _download_image("https://example.com/image.jpg")
        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == (500, 500)

    @patch("listenbrainz.art.og_image.req.get")
    def test_download_image_failure_returns_none(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        result = _download_image("https://example.com/image.jpg")
        assert result is None

    @patch("listenbrainz.art.og_image.req.get")
    def test_download_image_http_error_returns_none(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_response
        result = _download_image("https://example.com/image.jpg")
        assert result is None

    @patch("listenbrainz.art.og_image.req.get")
    def test_download_image_rejects_invalid_content_type(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.close = MagicMock()
        mock_get.return_value = mock_response

        result = _download_image("https://example.com/image.jpg")
        assert result is None

    @patch("listenbrainz.art.og_image.req.get")
    def test_download_image_rejects_oversized_response(self, mock_get):
        oversized_chunk = b"x" * (_MAX_DOWNLOAD_SIZE + 1)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.iter_content.return_value = [oversized_chunk]
        mock_response.close = MagicMock()
        mock_get.return_value = mock_response

        result = _download_image("https://example.com/image.jpg")
        assert result is None

    @patch("listenbrainz.art.og_image.time.sleep")
    @patch("listenbrainz.art.og_image.req.get")
    def test_download_image_retries_on_transient_failure(self, mock_get, mock_sleep):
        """First attempt fails with a transient error, retry succeeds."""
        dummy_png = _create_dummy_png()

        fail_response = MagicMock()
        fail_response.raise_for_status.side_effect = Exception("502 Bad Gateway")

        success_response = MagicMock()
        success_response.headers = {"Content-Type": "image/png"}
        success_response.iter_content.return_value = [dummy_png]
        success_response.raise_for_status = MagicMock()
        success_response.close = MagicMock()

        mock_get.side_effect = [fail_response, success_response]

        result = _download_image("https://example.com/image.jpg")
        assert result is not None
        assert isinstance(result, Image.Image)
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch("listenbrainz.art.og_image.time.sleep")
    @patch("listenbrainz.art.og_image.req.get")
    def test_download_image_exhausts_retries(self, mock_get, mock_sleep):
        """Both attempts fail — should return None after exhausting retries."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("502 Bad Gateway")
        mock_get.return_value = mock_response

        result = _download_image("https://example.com/image.jpg")
        assert result is None
        assert mock_get.call_count == 2  # initial attempt + 1 retry
        mock_sleep.assert_called_once_with(1)


class TestGeneratePlaylistOgImage:

    def _create_overlay_file(self, tmp_path):
        """Create a temporary overlay PNG file."""
        overlay_path = tmp_path / "og-overlay.png"
        img = Image.new("RGBA", (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT), (0, 0, 0, 0))
        img.save(overlay_path, format="PNG")
        return overlay_path

    def test_empty_urls_returns_none(self, tmp_path):
        overlay_path = self._create_overlay_file(tmp_path)
        result = generate_playlist_og_image([], overlay_path=overlay_path)
        assert result is None

    @patch("listenbrainz.art.og_image._download_image")
    def test_single_url_creates_single_composition(self, mock_download, tmp_path):
        overlay_path = self._create_overlay_file(tmp_path)
        mock_download.return_value = Image.new("RGBA", (500, 500), (255, 0, 0, 255))

        result = generate_playlist_og_image(
            ["https://example.com/art1.jpg"],
            overlay_path=overlay_path,
        )
        assert result is not None

        result_img = Image.open(result)
        assert result_img.size == (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT)
        assert result_img.mode == "RGB"

        assert mock_download.call_count == 1

    @patch("listenbrainz.art.og_image._download_image")
    def test_four_urls_creates_grid_composition(self, mock_download, tmp_path):
        overlay_path = self._create_overlay_file(tmp_path)
        mock_download.return_value = Image.new("RGBA", (500, 500), (0, 255, 0, 255))

        urls = [f"https://example.com/art{i}.jpg" for i in range(4)]
        result = generate_playlist_og_image(urls, overlay_path=overlay_path)
        assert result is not None

        result_img = Image.open(result)
        assert result_img.size == (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT)
        assert result_img.mode == "RGB"

        assert mock_download.call_count == 4

    @patch("listenbrainz.art.og_image._compose_single", wraps=_compose_single)
    @patch("listenbrainz.art.og_image._compose_grid_2x2", wraps=_compose_grid_2x2)
    @patch("listenbrainz.art.og_image._download_image")
    def test_three_urls_falls_back_to_single(self, mock_download, mock_grid, mock_single, tmp_path):
        """With < 4 URLs, should use single first image instead of grid."""
        overlay_path = self._create_overlay_file(tmp_path)
        mock_download.return_value = Image.new("RGBA", (500, 500), (0, 0, 255, 255))

        urls = [f"https://example.com/art{i}.jpg" for i in range(3)]
        result = generate_playlist_og_image(urls, overlay_path=overlay_path)
        assert result is not None

        assert mock_download.call_count == 1
        assert mock_single.call_count == 1
        assert mock_grid.call_count == 0

    @patch("listenbrainz.art.og_image._compose_single", wraps=_compose_single)
    @patch("listenbrainz.art.og_image._compose_grid_2x2", wraps=_compose_grid_2x2)
    @patch("listenbrainz.art.og_image._download_image")
    def test_four_urls_all_succeed_creates_grid(self, mock_download, mock_grid, mock_single, tmp_path):
        """With exactly 4 URLs all succeeding, the 2x2 grid should be composed."""
        overlay_path = self._create_overlay_file(tmp_path)
        good_img = Image.new("RGBA", (500, 500), (255, 0, 0, 255))
        mock_download.return_value = good_img

        urls = [f"https://example.com/art{i}.jpg" for i in range(4)]
        result = generate_playlist_og_image(urls, overlay_path=overlay_path)
        assert result is not None

        result_img = Image.open(result)
        assert result_img.size == (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT)

        assert mock_download.call_count == 4
        assert mock_grid.call_count == 1
        assert mock_single.call_count == 0

    @patch("listenbrainz.art.og_image._compose_single", wraps=_compose_single)
    @patch("listenbrainz.art.og_image._compose_grid_2x2", wraps=_compose_grid_2x2)
    @patch("listenbrainz.art.og_image._download_image")
    def test_download_failure_with_four_urls_falls_back_to_single(self, mock_download, mock_grid, mock_single, tmp_path):
        """If some of the 4 downloads fail, fall back to single image."""
        overlay_path = self._create_overlay_file(tmp_path)
        good_img = Image.new("RGBA", (500, 500), (255, 0, 0, 255))
        # Two good ones, two fails
        mock_download.side_effect = [good_img, good_img, None, None]

        urls = [f"https://example.com/art{i}.jpg" for i in range(4)]
        result = generate_playlist_og_image(urls, overlay_path=overlay_path)
        assert result is not None

        result_img = Image.open(result)
        assert result_img.size == (OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT)

        assert mock_download.call_count == 4
        assert mock_single.call_count == 1
        assert mock_grid.call_count == 0

    @patch("listenbrainz.art.og_image._download_image")
    def test_all_downloads_fail_returns_none(self, mock_download, tmp_path):
        """When all download attempts fail, returns None — tries every URL."""
        overlay_path = self._create_overlay_file(tmp_path)
        mock_download.return_value = None

        urls = [f"https://example.com/art{i}.jpg" for i in range(3)]
        result = generate_playlist_og_image(urls, overlay_path=overlay_path)
        assert result is None
        # all 3 URLs should be attempted before giving up
        assert mock_download.call_count == 3

    @patch("listenbrainz.art.og_image._download_image")
    def test_missing_overlay_returns_none(self, mock_download):
        result = generate_playlist_og_image(
            ["https://example.com/art1.jpg"],
            overlay_path="/nonexistent/path/overlay.png",
        )
        assert result is None
        assert mock_download.call_count == 0

    @patch("listenbrainz.art.og_image._download_image")
    def test_output_starts_with_png_magic_bytes(self, mock_download, tmp_path):
        overlay_path = self._create_overlay_file(tmp_path)
        mock_download.return_value = Image.new("RGBA", (500, 500), (255, 0, 0, 255))

        result = generate_playlist_og_image(
            ["https://example.com/art1.jpg"],
            overlay_path=overlay_path,
        )
        assert result is not None
        data = result.getvalue()
        # first 4 bytes of any valid PNG are 0x89 followed by "PNG" (RFC 2083 Section 3.1)
        assert data[:4] == b'\x89PNG'


class PlaylistOgImageEndpointTestCase(IntegrationTestCase):

    @patch("listenbrainz.webserver.views.art_api.CoverArtGenerator")
    @patch("listenbrainz.webserver.views.art_api.generate_playlist_og_image")
    @patch("listenbrainz.webserver.views.art_api.get_cover_art_options")
    @patch("listenbrainz.webserver.views.art_api.fetch_playlist_recording_metadata")
    @patch("listenbrainz.webserver.views.art_api.db_playlist.get_by_mbid")
    def test_og_image_success(self, mock_get_playlist, mock_fetch_metadata,
                              mock_get_cover_options, mock_generate_og, mock_cac_class):
        mock_playlist = MagicMock()
        mock_playlist.is_visible_by.return_value = True
        mock_recordings = []
        for i in range(4):
            rec = MagicMock()
            rec.mbid = f"e757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d{i}"
            mock_recordings.append(rec)
        mock_playlist.recordings = mock_recordings
        mock_get_playlist.return_value = mock_playlist

        mock_cac = MagicMock()
        mock_cac.resolve_cover_art.side_effect = lambda caa_id, caa_release_mbid, size: \
            f"https://archive.org/download/mbid-{caa_release_mbid}/mbid-{caa_release_mbid}-{caa_id}_thumb{size}.jpg"
        mock_cac_class.return_value = mock_cac

        mock_get_cover_options.return_value = [
            {
                "caa_id": 12345 + i,
                "caa_release_mbid": f"b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d{i}",
                "title": f"Track {i}",
                "entity_mbid": f"e757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d{i}",
                "artist": f"Artist {i}",
            }
            for i in range(4)
        ]

        dummy_png_buf = io.BytesIO(_create_dummy_png(OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT))
        mock_generate_og.return_value = dummy_png_buf

        resp = self.client.get(
            self.custom_url_for('art_api_v1.playlist_og_image',
                                playlist_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"))
        self.assert200(resp)
        self.assertEqual(resp.content_type, "image/png")
        # first 4 bytes of a valid PNG: 0x89 + "PNG" (RFC 2083 §3.1)
        self.assertTrue(resp.data[:4] == b'\x89PNG')

        self.assertIn("max-age=86400", resp.headers.get("Cache-Control", ""))
        self.assertIsNotNone(resp.headers.get("ETag"))

    @patch("listenbrainz.webserver.views.art_api.db_playlist.get_by_mbid")
    def test_og_image_playlist_not_found(self, mock_get_playlist):
        mock_get_playlist.return_value = None

        resp = self.client.get(
            self.custom_url_for('art_api_v1.playlist_og_image',
                                playlist_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"))
        self.assert404(resp)

    @patch("listenbrainz.webserver.views.art_api.db_playlist.get_by_mbid")
    def test_og_image_private_playlist(self, mock_get_playlist):
        mock_playlist = MagicMock()
        mock_playlist.is_visible_by.return_value = False
        mock_get_playlist.return_value = mock_playlist

        resp = self.client.get(
            self.custom_url_for('art_api_v1.playlist_og_image',
                                playlist_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"))
        self.assert404(resp)

    @patch("listenbrainz.webserver.views.art_api.get_cover_art_options")
    @patch("listenbrainz.webserver.views.art_api.fetch_playlist_recording_metadata")
    @patch("listenbrainz.webserver.views.art_api.db_playlist.get_by_mbid")
    def test_og_image_no_cover_art_redirects_to_default(self, mock_get_playlist, mock_fetch_metadata,
                                                        mock_get_cover_options):
        mock_playlist = MagicMock()
        mock_playlist.is_visible_by.return_value = True
        rec = MagicMock()
        rec.mbid = "e757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d0"
        mock_playlist.recordings = [rec]
        mock_get_playlist.return_value = mock_playlist

        mock_get_cover_options.return_value = []

        resp = self.client.get(
            self.custom_url_for('art_api_v1.playlist_og_image',
                                playlist_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"))
        self.assertStatus(resp, 302)
        self.assertIn("share-header.png", resp.headers.get("Location", ""))

    @patch("listenbrainz.webserver.views.art_api.CoverArtGenerator")
    @patch("listenbrainz.webserver.views.art_api.generate_playlist_og_image")
    @patch("listenbrainz.webserver.views.art_api.get_cover_art_options")
    @patch("listenbrainz.webserver.views.art_api.fetch_playlist_recording_metadata")
    @patch("listenbrainz.webserver.views.art_api.db_playlist.get_by_mbid")
    def test_og_image_generation_failure_redirects_to_default(self, mock_get_playlist, mock_fetch_metadata,
                                                              mock_get_cover_options, mock_generate_og,
                                                              mock_cac_class):
        mock_playlist = MagicMock()
        mock_playlist.is_visible_by.return_value = True
        rec = MagicMock()
        rec.mbid = "e757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d0"
        mock_playlist.recordings = [rec]
        mock_get_playlist.return_value = mock_playlist

        mock_cac = MagicMock()
        mock_cac.resolve_cover_art.return_value = "https://archive.org/download/mbid-test/thumb500.jpg"
        mock_cac_class.return_value = mock_cac

        mock_get_cover_options.return_value = [
            {
                "caa_id": 12345,
                "caa_release_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "title": "Track 1",
                "entity_mbid": "e757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "artist": "Artist 1",
            }
        ]

        mock_generate_og.return_value = None

        resp = self.client.get(
            self.custom_url_for('art_api_v1.playlist_og_image',
                                playlist_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"))
        self.assertStatus(resp, 302)
        self.assertIn("share-header.png", resp.headers.get("Location", ""))

    @patch("listenbrainz.webserver.views.art_api.CoverArtGenerator")
    @patch("listenbrainz.webserver.views.art_api.generate_playlist_og_image")
    @patch("listenbrainz.webserver.views.art_api.get_cover_art_options")
    @patch("listenbrainz.webserver.views.art_api.fetch_playlist_recording_metadata")
    @patch("listenbrainz.webserver.views.art_api.db_playlist.get_by_mbid")
    def test_og_image_etag_returns_304(self, mock_get_playlist, mock_fetch_metadata,
                                       mock_get_cover_options, mock_generate_og, mock_cac_class):
        mock_playlist = MagicMock()
        mock_playlist.is_visible_by.return_value = True
        mock_recordings = []
        for i in range(4):
            rec = MagicMock()
            rec.mbid = f"e757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d{i}"
            mock_recordings.append(rec)
        mock_playlist.recordings = mock_recordings
        mock_get_playlist.return_value = mock_playlist

        mock_cac = MagicMock()
        mock_cac.resolve_cover_art.side_effect = lambda caa_id, caa_release_mbid, size: \
            f"https://archive.org/download/mbid-{caa_release_mbid}/mbid-{caa_release_mbid}-{caa_id}_thumb{size}.jpg"
        mock_cac_class.return_value = mock_cac

        mock_get_cover_options.return_value = [
            {
                "caa_id": 12345 + i,
                "caa_release_mbid": f"b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d{i}",
                "title": f"Track {i}",
                "entity_mbid": f"e757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d{i}",
                "artist": f"Artist {i}",
            }
            for i in range(4)
        ]

        dummy_png_buf = io.BytesIO(_create_dummy_png(OPENGRAPH_IMAGE_WIDTH, OPENGRAPH_IMAGE_HEIGHT))
        mock_generate_og.return_value = dummy_png_buf

        # First request to get the ETag
        resp = self.client.get(
            self.custom_url_for('art_api_v1.playlist_og_image',
                                playlist_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"))
        self.assert200(resp)
        etag = resp.headers.get("ETag")
        self.assertIsNotNone(etag)

        # Second request with If-None-Match should return 304
        # and skip the expensive fetch_playlist_recording_metadata call
        mock_fetch_metadata.reset_mock()
        resp = self.client.get(
            self.custom_url_for('art_api_v1.playlist_og_image',
                                playlist_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"),
            headers={"If-None-Match": etag})
        self.assertStatus(resp, 304)
        mock_fetch_metadata.assert_not_called()
