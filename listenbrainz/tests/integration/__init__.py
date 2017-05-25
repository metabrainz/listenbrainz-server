from __future__ import absolute_import
import sys
import os

from listenbrainz.webserver.testing import ServerTestCase
from listenbrainz.db.testing import DatabaseTestCase

class IntegrationTestCase(ServerTestCase, DatabaseTestCase):

    TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'testdata')
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def path_to_data_file(self, fn):
        """ Returns the path of the test data file relative to the test file.

            Args:
                fn: the name of the data file
        """
        return os.path.join(IntegrationTestCase.TEST_DATA_PATH, fn)
