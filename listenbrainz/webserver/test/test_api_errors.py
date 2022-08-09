from listenbrainz.tests.integration import IntegrationTestCase

from unittest import mock
from werkzeug.exceptions import InternalServerError


class APIErrorTestCase(IntegrationTestCase):

    @mock.patch('listenbrainz.webserver.views.stats_api.db_user.get_by_mb_id')
    def test_api_error_unexpected_error_returns_json(self, mock_db_get):
        mock_db_get.side_effect = InternalServerError("Some bad thing happened")
        r = self.client.get('/1/stats/user/iliekcomputers/artists')
        self.assert500(r)
        self.assertEqual(r.json['error'], 'An unknown error occured.')
