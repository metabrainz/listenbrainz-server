import datetime

from freezegun import freeze_time

from listenbrainz.domain.spotify import SpotifyService
from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class ExternalServiceTestCase(NonAPIIntegrationTestCase):

    @freeze_time("2021-05-12 03:21:34", tz_offset=0)
    def test_user_oauth_token_has_expired(self):
        service = SpotifyService()

        # has expired
        user = {'token_expires': datetime.datetime(2021, 5, 12, 3, 0, 40, tzinfo=datetime.timezone.utc)}
        assert service.user_oauth_token_has_expired(user) is True

        # expires within the 5 minute threshold
        user = {'token_expires': datetime.datetime(2021, 5, 12, 3, 24, 40, tzinfo=datetime.timezone.utc)}
        assert service.user_oauth_token_has_expired(user) is True

        # hasn't expired
        user = {'token_expires': datetime.datetime(2021, 5, 12, 4, 1, 40, tzinfo=datetime.timezone.utc)}
        assert service.user_oauth_token_has_expired(user) is False
