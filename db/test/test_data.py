from db.testing import DatabaseTestCase, TEST_DATA_PATH
from db import data
import os.path
import json


class DataTestCase(DatabaseTestCase):

    def setUp(self):
        super(DataTestCase, self).setUp()

    # TODO: Don't be lazy, write some tests!
