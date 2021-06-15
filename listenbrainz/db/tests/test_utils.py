# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError
import unittest

import listenbrainz.db.model.utils as utils


class ModelUtilsTestCase(unittest.TestCase):
    def test_check_rec_mbid_msid_is_valid_uuid(self):

        # test invalid UUID formats
        with self.assertRaises(ValueError):
            utils.check_rec_mbid_msid_is_valid_uuid("foobar")

        with self.assertRaises(ValueError):
            utils.check_rec_mbid_msid_is_valid_uuid("12345")

        # test valid UUID formats
        mbid_to_test = "9273e0e6-2182-4a6a-beb2-b6ab661d1e66"
        result = utils.check_rec_mbid_msid_is_valid_uuid(mbid_to_test)
        self.assertEqual(result, "9273e0e6-2182-4a6a-beb2-b6ab661d1e66")

    def test_check_datetime_has_tzinfo_or_set_now(self):

        # test invalid datetime formats
        with self.assertRaises(ValueError):
            utils.check_datetime_has_tzinfo_or_set_now(datetime.now())

        with self.assertRaises(ValueError):
            utils.check_datetime_has_tzinfo_or_set_now("foobar")

        with self.assertRaises(ValueError):
            utils.check_datetime_has_tzinfo_or_set_now(-12345)

        # test valid datetime with tzinfo
        now = datetime.now(timezone.utc)
        result = utils.check_datetime_has_tzinfo_or_set_now(now)
        self.assertEqual(result, now)

        # test that function returns now() if no argument is provided
        result = utils.check_datetime_has_tzinfo_or_set_now()
        self.assertGreater(result, now)
