from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import UUID

from datasethoster import RequestSource
from pydantic import ValidationError
from werkzeug.exceptions import BadRequest

from listenbrainz.labs_api.labs.api.bulk_tag_lookup import BulkTagLookup, BulkTagLookupInput


RECORDING_MBID = "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
OTHER_RECORDING_MBID = "0e3fc579-2d24-4f20-9dae-736e1ec78798"


class BulkTagLookupInputTestCase(TestCase):

    def test_recording_mbid_is_parsed_as_uuid(self):
        params = BulkTagLookupInput(recording_mbid=RECORDING_MBID)

        self.assertEqual(params.recording_mbid, [UUID(RECORDING_MBID)])

    def test_comma_separated_mbids_are_parsed_as_uuids(self):
        params = BulkTagLookupInput(
            recording_mbid=f" {RECORDING_MBID}, , {OTHER_RECORDING_MBID}, "
        )

        self.assertEqual(params.recording_mbid, [UUID(RECORDING_MBID), UUID(OTHER_RECORDING_MBID)])

    def test_uuid_list_is_accepted(self):
        params = BulkTagLookupInput(recording_mbid=[RECORDING_MBID, OTHER_RECORDING_MBID])

        self.assertEqual(params.recording_mbid, [UUID(RECORDING_MBID), UUID(OTHER_RECORDING_MBID)])

    def test_comma_separated_get_parameter_list_is_accepted(self):
        # Dataset Hoster wraps GET parameters in a list for list-typed fields.
        params = BulkTagLookupInput(recording_mbid=[f"{RECORDING_MBID},{OTHER_RECORDING_MBID}"])

        self.assertEqual(params.recording_mbid, [UUID(RECORDING_MBID), UUID(OTHER_RECORDING_MBID)])

    def test_uuid_object_is_accepted(self):
        params = BulkTagLookupInput(recording_mbid=UUID(RECORDING_MBID))

        self.assertEqual(params.recording_mbid, [UUID(RECORDING_MBID)])

    def test_invalid_recording_mbid_is_rejected(self):
        for value in ("not-a-uuid", f"{RECORDING_MBID},not-a-uuid", [RECORDING_MBID, "not-a-uuid"]):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                BulkTagLookupInput(recording_mbid=value)


class BulkTagLookupTestCase(TestCase):

    def setUp(self):
        self.engine = MagicMock()
        self.enterContext(patch("listenbrainz.labs_api.labs.api.bulk_tag_lookup.timescale.engine", self.engine))
        self.cursor = self.engine.raw_connection.return_value.cursor.return_value.__enter__.return_value
        self.cursor.fetchone.side_effect = [
            {
                "recording_mbid": RECORDING_MBID,
                "tag": "rock",
                "tag_count": 2,
                "percent": 100.0,
                "source": "recording",
            },
            {
                "recording_mbid": OTHER_RECORDING_MBID,
                "tag": "pop",
                "tag_count": 1,
                "percent": 100.0,
                "source": "recording",
            },
            None,
        ]

    def test_lookup_flattens_mbids_across_input_objects(self):
        params = [
            BulkTagLookupInput(recording_mbid=f"{RECORDING_MBID},{OTHER_RECORDING_MBID}"),
            BulkTagLookupInput(recording_mbid=RECORDING_MBID),
        ]

        output = BulkTagLookup().fetch(params, RequestSource.json_post)

        self.assertEqual(self.cursor.execute.call_args.args[1], (
            (UUID(RECORDING_MBID), UUID(OTHER_RECORDING_MBID), UUID(RECORDING_MBID)),
        ))
        self.assertEqual([row.recording_mbid for row in output], [UUID(RECORDING_MBID), UUID(OTHER_RECORDING_MBID)])

    def test_empty_input_skips_database(self):
        for params in ([], [BulkTagLookupInput(recording_mbid=" , ")]):
            with self.subTest(params=params):
                self.assertEqual(BulkTagLookup().fetch(params, RequestSource.json_get), [])
        self.engine.raw_connection.assert_not_called()

    def test_limit_counts_mbids_across_input_objects(self):
        params = [
            BulkTagLookupInput(recording_mbid=",".join([RECORDING_MBID] * 500)),
            BulkTagLookupInput(recording_mbid=",".join([OTHER_RECORDING_MBID] * 501)),
        ]

        with self.assertRaises(BadRequest):
            BulkTagLookup().fetch(params, RequestSource.json_post)
        self.engine.raw_connection.assert_not_called()

    def test_exactly_one_thousand_mbids_are_allowed(self):
        params = [BulkTagLookupInput(recording_mbid=",".join([RECORDING_MBID] * 1000))]

        BulkTagLookup().fetch(params, RequestSource.json_post)

        self.assertEqual(len(self.cursor.execute.call_args.args[1][0]), 1000)
