import unittest
from unittest import mock

from flask import Flask

from listenbrainz.background.listens_importer.youtubemusic import YouTubeMusicListensImporter
from listenbrainz.metadata_cache.youtube.handler import YouTubeCacheHandler
from listenbrainz.metadata_cache.youtube.models import YouTubeVideo


class YouTubeMusicImporterTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.importer = YouTubeMusicListensImporter(None, None)
        self.item = {
            "titleUrl": "https://www.youtube.com/watch?v=2o9aoL0NWpw",
            "time": "2021-12-18T10:33:36Z",
        }
        self.metadata = {
            "2o9aoL0NWpw": YouTubeVideo(
                video_id="2o9aoL0NWpw",
                title="Watched You Fall",
                channel_name="Test Artist - Topic",
            ),
        }

    def test_recovers_unusable_titles_with_or_without_channel(self):
        titles = [
            {},
            {"title": None},
            {"title": ""},
            {"title": " \t "},
            {"title": "Watched "},
            {"title": "Watched \t "},
            {"title": self.item["titleUrl"]},
            {"title": "Watched " + self.item["titleUrl"]},
            {"title": "Watched https://music.youtube.com/watch?v=2o9aoL0NWpw"},
            {"title": "Watched http://www.youtube.com/watch?v=2o9aoL0NWpw"},
        ]
        for title in titles:
            for subtitles in ([], [{"name": "Existing Artist"}]):
                with self.subTest(title=title, subtitles=subtitles):
                    item = {**self.item, **title, "subtitles": subtitles}
                    with self.app.app_context(), mock.patch.object(
                        YouTubeCacheHandler, "lookup", return_value=self.metadata
                    ) as lookup:
                        listens = self.importer.parse_listen_batch([item])

                    lookup.assert_called_once_with(["2o9aoL0NWpw"])
                    self.assertEqual(len(listens), 1)
                    self.assertEqual(listens[0]["track_metadata"]["track_name"], "Watched You Fall")
                    self.assertEqual(listens[0]["track_metadata"]["artist_name"], "Test Artist")

    def test_recovers_missing_channel(self):
        missing_channels = [
            {},
            {"subtitles": []},
            {"subtitles": None},
            {"subtitles": [{}]},
            {"subtitles": [{"name": None}]},
            {"subtitles": [{"name": 123}]},
            {"subtitles": [{"name": ""}]},
            {"subtitles": [{"name": " \t "}]},
        ]
        for subtitles in missing_channels:
            with self.subTest(subtitles=subtitles):
                item = {**self.item, "title": "Watched You Fall", **subtitles}
                with self.app.app_context(), mock.patch.object(
                    YouTubeCacheHandler, "lookup", return_value=self.metadata
                ) as lookup:
                    listens = self.importer.parse_listen_batch([item])

                lookup.assert_called_once_with(["2o9aoL0NWpw"])
                self.assertEqual(len(listens), 1)
                self.assertEqual(listens[0]["track_metadata"]["track_name"], "Watched You Fall")
                self.assertEqual(listens[0]["track_metadata"]["artist_name"], "Test Artist")

    def test_usable_metadata_does_not_call_cache(self):
        item = {
            **self.item,
            "title": "Watched Watched You Fall",
            "subtitles": [{"name": "Test Artist - Topic"}],
        }
        with self.app.app_context(), mock.patch.object(YouTubeCacheHandler, "lookup") as lookup:
            listens = self.importer.parse_listen_batch([item])

        lookup.assert_not_called()
        self.assertEqual(listens[0]["track_metadata"]["track_name"], "Watched You Fall")

    def test_invalid_video_id_does_not_call_cache(self):
        invalid_fields = [
            {"titleUrl": ""},
            {"titleUrl": "https://youtu.be/invalid"},
        ]
        for invalid in invalid_fields:
            with self.subTest(invalid=invalid):
                item = {**self.item, "title": "Watched " + self.item["titleUrl"], **invalid}
                with self.app.app_context(), mock.patch.object(YouTubeCacheHandler, "lookup") as lookup:
                    listens = self.importer.parse_listen_batch([item])

                lookup.assert_not_called()
                self.assertEqual(listens, [])

    def test_unresolved_url_title_is_not_imported(self):
        item = {
            **self.item,
            "title": "Watched " + self.item["titleUrl"],
            "subtitles": [{"name": "Existing Artist"}],
        }
        with self.app.app_context(), mock.patch.object(YouTubeCacheHandler, "lookup", return_value={}) as lookup:
            listens = self.importer.parse_listen_batch([item])

        lookup.assert_called_once_with(["2o9aoL0NWpw"])
        self.assertEqual(listens, [])
