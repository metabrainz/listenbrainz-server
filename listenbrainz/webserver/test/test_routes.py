import flask

from listenbrainz.webserver import API_PREFIX
from listenbrainz.webserver.testing import ServerTestCase


class RoutesTestCase(ServerTestCase):

    def test_routes_have_trailing_slash(self):
        """Check that all user-facing routes have a trailing /"""

        # We don't check some rules.
        # Don't add a / to API endpoints, because a redirect on a POST from an external client
        #  may result in unexpected results
        # Admin endpoints are maintained by flask-admin
        ignored_prefixes = (API_PREFIX, '/admin', '/static')
        # Specific endpoint for deleting accounts from musicbrainz-server (MBS-9680)
        ignored_endpoints = {'index.mb_user_deleter'}

        for rule in flask.current_app.url_map.iter_rules():
            if not rule.rule.startswith(ignored_prefixes) and rule.endpoint not in ignored_endpoints:
                if not rule.rule.endswith('/'):
                    self.fail(f"Rule doesn't end with a trailing slash: {rule.rule} ({rule.endpoint})")
