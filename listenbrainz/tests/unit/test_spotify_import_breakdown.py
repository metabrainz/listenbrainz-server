import io
import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from listenbrainz.tools.spotify_import_breakdown import (
    Breakdown, IMPORTED, INCOGNITO, INVALID, NEEDS_LOOKUP, NO_TRACK_LINK,
    SHORT_PLAY, analyze_path, classify_entry, is_account_data_history,
    matches_import_filter,
)


def _entry(**overrides):
    """ A well-formed extended-streaming-history entry that would be imported. """
    entry = {
        "ts": "2023-05-04T10:23:45Z",
        "ms_played": 215000,
        "master_metadata_track_name": "Immigrant Song",
        "master_metadata_album_artist_name": "Led Zeppelin",
        "master_metadata_album_name": "Led Zeppelin III",
        "spotify_track_uri": "spotify:track:78lgmZwycJ3nzsdgmPPGNx",
        "reason_start": "clickrow",
        "reason_end": "trackdone",
        "skipped": False,
        "incognito_mode": False,
    }
    entry.update(overrides)
    return entry


class ClassifyEntryTestCase(unittest.TestCase):
    """ The classification must mirror SpotifyListensImporter's skip rules. """

    def test_normal_play_is_imported(self):
        self.assertEqual(classify_entry(_entry())[0], IMPORTED)

    def test_incognito_is_skipped_even_when_played_fully(self):
        self.assertEqual(classify_entry(_entry(incognito_mode=True))[0], INCOGNITO)

    def test_short_play_with_skipped_flag(self):
        category, detail = classify_entry(_entry(ms_played=5000, skipped=True))
        self.assertEqual(category, SHORT_PLAY)
        self.assertEqual(detail, "skipped flag")

    def test_short_play_with_skip_reason(self):
        category, detail = classify_entry(_entry(ms_played=5000, reason_end="fwdbtn"))
        self.assertEqual(category, SHORT_PLAY)
        self.assertEqual(detail, "reason_end=fwdbtn")

    def test_short_play_with_null_reason_end_is_skipped(self):
        # None is part of SKIP_REASONS in the importer
        self.assertEqual(classify_entry(_entry(ms_played=5000, reason_end=None))[0], SHORT_PLAY)

    def test_short_play_that_ended_normally_is_imported(self):
        # under 30s but reason_end=trackdone and not skipped -> imported
        self.assertEqual(classify_entry(_entry(ms_played=15000))[0], IMPORTED)

    def test_long_play_with_skip_reason_is_imported(self):
        # 30s or more is imported regardless of how it ended
        self.assertEqual(classify_entry(_entry(ms_played=30000, reason_end="fwdbtn"))[0], IMPORTED)

    def test_podcast_episode_has_no_track_link(self):
        category, detail = classify_entry(_entry(
            spotify_track_uri=None,
            spotify_episode_uri="spotify:episode:4d0dcgoZbnWjcRj4H0nlWc",
            master_metadata_track_name=None,
            master_metadata_album_artist_name=None,
        ))
        self.assertEqual(category, NO_TRACK_LINK)
        self.assertEqual(detail, "podcast episode")

    def test_malformed_track_uri_has_no_track_link(self):
        self.assertEqual(classify_entry(_entry(spotify_track_uri="garbage"))[0], NO_TRACK_LINK)

    def test_missing_names_need_metadata_lookup(self):
        entry = _entry(master_metadata_track_name=None, master_metadata_album_artist_name=None)
        self.assertEqual(classify_entry(entry)[0], NEEDS_LOOKUP)

    def test_missing_timestamp_is_invalid(self):
        entry = _entry()
        del entry["ts"]
        self.assertEqual(classify_entry(entry)[0], INVALID)

    def test_malformed_timestamp_is_invalid(self):
        self.assertEqual(classify_entry(_entry(ts="04/05/2023"))[0], INVALID)

    def test_incognito_wins_over_short_play(self):
        # same precedence as the importer: incognito is checked first
        self.assertEqual(classify_entry(_entry(incognito_mode=True, ms_played=5000, skipped=True))[0], INCOGNITO)


class FileFilterTestCase(unittest.TestCase):
    """ The file filter must mirror SpotifyListensImporter.filter_zip_file. """

    def test_extended_history_files_match(self):
        self.assertTrue(matches_import_filter("Spotify Extended Streaming History/Streaming_History_Audio_2023_1.json"))
        self.assertTrue(matches_import_filter("endsong_0.json"))

    def test_video_and_misc_files_do_not_match(self):
        self.assertFalse(matches_import_filter("Streaming_History_Video_2023.json"))
        self.assertFalse(matches_import_filter("ReadMeFirst_ExtendedStreamingHistory.pdf"))

    def test_account_data_export_detection(self):
        self.assertTrue(is_account_data_history("StreamingHistory_music_0.json"))
        self.assertFalse(is_account_data_history("Streaming_History_Audio_2023_1.json"))


class AnalyzeZipTestCase(unittest.TestCase):

    def test_zip_breakdown(self):
        audio_entries = [
            _entry(),
            _entry(ms_played=3000, skipped=True),
            _entry(incognito_mode=True),
            _entry(spotify_track_uri=None, spotify_episode_uri="spotify:episode:x",
                   master_metadata_track_name=None, master_metadata_album_artist_name=None),
        ]
        with TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "my_spotify_data.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("Spotify Extended Streaming History/Streaming_History_Audio_2023_1.json",
                            json.dumps(audio_entries))
                zf.writestr("Spotify Extended Streaming History/Streaming_History_Video_2023.json",
                            json.dumps([_entry()]))

            breakdown = Breakdown(max_examples=5)
            analyze_path(zip_path, breakdown)

        self.assertEqual(breakdown.total, 4)
        self.assertEqual(breakdown.counts[IMPORTED], 1)
        self.assertEqual(breakdown.counts[SHORT_PLAY], 1)
        self.assertEqual(breakdown.counts[INCOGNITO], 1)
        self.assertEqual(breakdown.counts[NO_TRACK_LINK], 1)
        self.assertEqual(len(breakdown.files_scanned), 1)
        # the video file is ignored, exactly like the importer ignores it
        self.assertEqual(len(breakdown.files_ignored), 1)

    def test_account_data_zip_produces_warning_not_entries(self):
        with TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "my_data.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("MyData/StreamingHistory_music_0.json",
                            json.dumps([{"endTime": "2023-05-04 10:23", "msPlayed": 215000,
                                         "artistName": "Led Zeppelin", "trackName": "Immigrant Song"}]))

            breakdown = Breakdown(max_examples=5)
            analyze_path(zip_path, breakdown)

        self.assertEqual(breakdown.total, 0)
        self.assertEqual(len(breakdown.account_data_files), 1)

    def test_single_json_file(self):
        with TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "Streaming_History_Audio_2024_2.json"
            json_path.write_text(json.dumps([_entry(), _entry(ms_played=100, reason_end="backbtn")]))

            breakdown = Breakdown(max_examples=5)
            analyze_path(json_path, breakdown)

        self.assertEqual(breakdown.total, 2)
        self.assertEqual(breakdown.counts[IMPORTED], 1)
        self.assertEqual(breakdown.counts[SHORT_PLAY], 1)
