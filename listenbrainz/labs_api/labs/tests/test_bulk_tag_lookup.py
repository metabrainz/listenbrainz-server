from unittest import TestCase
from uuid import UUID

from pydantic import ValidationError

from listenbrainz.labs_api.labs.api.bulk_tag_lookup import BulkTagLookupInput


class BulkTagLookupInputTestCase(TestCase):

    def test_recording_mbid_is_parsed_as_uuid(self):
        recording_mbid = "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"

        params = BulkTagLookupInput(recording_mbid=recording_mbid)

        self.assertEqual(params.recording_mbid, UUID(recording_mbid))

    def test_invalid_recording_mbid_is_rejected(self):
        with self.assertRaises(ValidationError):
            BulkTagLookupInput(recording_mbid="not-a-uuid")
