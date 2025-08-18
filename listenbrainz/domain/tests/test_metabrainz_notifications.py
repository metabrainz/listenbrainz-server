from unittest.mock import patch, MagicMock
from listenbrainz.domain import metabrainz_notifications
from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class MetabrainNotificationsTestCase(NonAPIIntegrationTestCase):
    @patch("listenbrainz.domain.metabrainz_notifications.send_multiple_notifications")
    def test_send_notification(self, mock_send_multiple):
        metabrainz_notifications.send_notification(
            subject="Test Subject",
            body="Test Body",
            musicbrainz_row_id=123,
            user_email="test@example.com",
            from_addr="sender@example.com",
        )
        expected_notification = [
            [
                {
                    "subject": "Test Subject",
                    "body": "Test Body",
                    "user_id": 123,
                    "to": "test@example.com",
                    "project": "listenbrainz",
                    "sent_from": "sender@example.com",
                    "send_email": True,
                    "important": True,
                    "expire_age": 7,
                }
            ]
        ]

        mock_send_multiple.assert_called_once_with(expected_notification)

    @patch("listenbrainz.domain.metabrainz_notifications._fetch_token")
    @patch("requests.post")
    def test_send_multiple_notifications(self, mock_post, mock_fetch_token):
        mock_fetch_token.return_value = "access_token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifications = [{"user_id": 1, "body": "Notification 1"}]

        metabrainz_notifications.send_multiple_notifications(notifications)

        mock_fetch_token.assert_called_once()
        expected_url = "https://metabrainz.org/notification/send"
        expected_headers = {"Authorization": "Bearer access_token"}
        mock_post.assert_called_once_with(
            url=expected_url, json=notifications, headers=expected_headers
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("listenbrainz.domain.metabrainz_notifications._fetch_token")
    @patch("requests.get")
    def test_get_digest_preference(self, mock_get, mock_fetch_token):
        mock_fetch_token.return_value = "access_token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"digest": True, "digest_age": 7}
        mock_get.return_value = mock_response

        result = metabrainz_notifications.get_digest_preference(musicbrainz_row_id=456)

        expected_url = "https://metabrainz.org/notification/456/digest-preference"
        mock_get.assert_called_once_with(
            url=expected_url, headers={"Authorization": "Bearer access_token"}
        )
        self.assertEqual(result, {"digest": True, "digest_age": 7})

    @patch("listenbrainz.domain.metabrainz_notifications._fetch_token")
    @patch("requests.post")
    def test_set_digest_preference(self, mock_post, mock_fetch_token):
        mock_fetch_token.return_value = "access_token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"digest": True, "digest_age": 14}
        mock_post.return_value = mock_response

        result = metabrainz_notifications.set_digest_preference(
            musicbrainz_row_id=789, digest=False, digest_age=14
        )

        expected_url = "https://metabrainz.org/notification/789/digest-preference"
        expected_data = {"digest": True, "digest_age": 14}
        mock_post.assert_called_once_with(
            url=expected_url, json=expected_data, headers={"Authorization": "Bearer access_token"}
        )
        self.assertEqual(result, {"digest": True, "digest_age": 14})
