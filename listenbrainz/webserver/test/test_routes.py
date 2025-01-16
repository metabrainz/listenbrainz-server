from listenbrainz.webserver import API_PREFIX
from listenbrainz.webserver.testing import ServerTestCase


class RoutesTestCase(ServerTestCase):

    def test_routes_have_trailing_slash(self):
        """Check that all user-facing routes have a trailing /"""

        # We don't check some rules.
        # Don't add a / to API endpoints, because a redirect on a POST from an external client
        #  may result in unexpected results
        # Admin endpoints are maintained by flask-admin
        ignored_prefixes = (API_PREFIX, '/admin', '/static', '/syndication-feed')
        # Specific endpoint for deleting accounts from musicbrainz-server (MBS-9680)
        ignored_endpoints = {'index.mb_user_deleter'}

        for rule in self.app.url_map.iter_rules():
            if not rule.rule.startswith(ignored_prefixes) and rule.endpoint not in ignored_endpoints:
                if not rule.rule.endswith('/'):
                    self.fail(f"Rule doesn't end with a trailing slash: {rule.rule} ({rule.endpoint})")


    def test_api_routes_have_options(self):
        """ Ensure that all API routes (which are cors-enabled) also add CORS headers to their options response.
        The flask default doesn't.
        """
        CORS_DISABLED_ENDPOINTS = set()
        for rule in self.app.url_map.iter_rules():
            if rule.rule.startswith(API_PREFIX) and rule.endpoint not in CORS_DISABLED_ENDPOINTS:
                with self.subTest(rule=rule):
                    url = rule.rule
                    # replace path args requiring an integer with arbitrary integer to ensure path matches
                    for arg in rule.arguments:
                        url = url.replace(f"<int:{arg}>", "1")
                    response = self.client.options(url)
                    headers = set(response.headers.keys())
                    self.assertIn("Access-Control-Allow-Origin", headers)
                    self.assertIn("Access-Control-Allow-Methods", headers)
                    self.assertIn("Access-Control-Max-Age", headers)
                    self.assertIn("Access-Control-Allow-Headers", headers)
