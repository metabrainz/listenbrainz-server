import io
import unittest
from listenbrainz.webserver.views.import_listens import parse_scrobbler_log

class ParseScrobblerLogTestCase(unittest.TestCase):
    def test_parse_scrobbler_log(self):
        # Prepare sample data
        scrobbler_log_content = (
            "# This is a comment\n"
            "Artist Name\tAlbum Name\tTrack Name\t1\t300\tL\t1600000000\tmbid-123\n"
            "Artist 2\tAlbum 2\tTrack 2\t2\t200\tS\t1600000100\t\n"
            "<Untagged>\tUnknown\tUnknown\t3\t0\t\t1600000200\t\n" # Should be skipped
            "Artist 3\tAlbum 3\tTrack 3\t\t\t\t1600000300\t\n" # Minimal valid
        )
        
        stream = io.BytesIO(scrobbler_log_content.encode('utf-8'))
        listens = parse_scrobbler_log(stream)

        self.assertEqual(len(listens), 3)
        
        # Verify first listen
        self.assertEqual(listens[0]['track_metadata']['artist_name'], 'Artist Name')
        self.assertEqual(listens[0]['track_metadata']['release_name'], 'Album Name')
        self.assertEqual(listens[0]['track_metadata']['track_name'], 'Track Name')
        self.assertEqual(listens[0]['track_metadata']['additional_info']['recording_mbid'], 'mbid-123')
        self.assertEqual(listens[0]['track_metadata']['additional_info']['rating'], 'L')
        self.assertEqual(listens[0]['listened_at'], 1600000000)

        # Verify second listen (no mbid)
        self.assertEqual(listens[1]['track_metadata']['artist_name'], 'Artist 2')
        self.assertNotIn('recording_mbid', listens[1]['track_metadata']['additional_info'])
        self.assertEqual(listens[1]['listened_at'], 1600000100)

        # Verify third listen (Artist 3)
        self.assertEqual(listens[2]['track_metadata']['artist_name'], 'Artist 3')
        self.assertEqual(listens[2]['listened_at'], 1600000300)

