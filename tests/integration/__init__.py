import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))

from webserver.testing import ServerTestCase
from db.testing import DatabaseTestCase

class IntegrationTestCase(ServerTestCase, DatabaseTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

