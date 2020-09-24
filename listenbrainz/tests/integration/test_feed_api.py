from listenbrainz.tests.integration.test_api import APITestCase
from flask import url_for, current_app

class FeedAPITestCase(APITestCase):

    def test_it_sends_listens_for_users_that_are_being_followed(self):
        pass

    def test_it_returns_not_found_for_non_existent_user(self):
        pass

    def test_it_honors_max_ts_and_min_ts(self):
        pass
