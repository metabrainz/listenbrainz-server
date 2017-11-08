
import sys
import os

from listenbrainz.webserver.testing import ServerTestCase, APICompatServerTestCase
from listenbrainz.db.testing import DatabaseTestCase

class IntegrationTestCase(ServerTestCase, DatabaseTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)


class APICompatIntegrationTestCase(APICompatServerTestCase, DatabaseTestCase):

    def setUp(self):
        APICompatServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

    def tearDown(self):
        APICompatServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)
