# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError
import unittest

import data.model.validators as validators


class ModelUtilsTestCase(unittest.TestCase):
    def test_check_valid_uuid(self):

        # test invalid UUID formats
        with self.assertRaises(ValueError):
            validators.check_valid_uuid("foobar")

        with self.assertRaises(ValueError):
            validators.check_valid_uuid("12345")

        # test valid UUID formats
        mbid_to_test = "9273e0e6-2182-4a6a-beb2-b6ab661d1e66"
        result = validators.check_valid_uuid(mbid_to_test)
        self.assertEqual(result, "9273e0e6-2182-4a6a-beb2-b6ab661d1e66")

    def test_check_datetime_has_tzinfo(self):

        # test invalid datetime formats
        with self.assertRaises(ValueError):
            validators.check_datetime_has_tzinfo(datetime.now())

        with self.assertRaises(ValueError):
            validators.check_datetime_has_tzinfo("foobar")

        with self.assertRaises(ValueError):
            validators.check_datetime_has_tzinfo(-12345)

        # test valid datetime with tzinfo
        now = datetime.now(timezone.utc)
        result = validators.check_datetime_has_tzinfo(now)
        self.assertEqual(result, now)
