from psycopg2 import DatabaseError

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase

from unittest import mock
from werkzeug.exceptions import InternalServerError


class APIErrorTestCase(DatabaseTestCase, ServerTestCase):

    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.app.config["TESTING"] = False

    @mock.patch('listenbrainz.webserver.views.stats_api.db_user.get_by_mb_id')
    def test_api_error_unexpected_error_returns_json(self, mock_db_get):
        mock_db_get.side_effect = DatabaseError()
        r = self.client.get('/1/stats/user/iliekcomputers/artists')
        self.assert500(r)
        self.assertEqual(r.json['error'], 'An unknown error occured.')
