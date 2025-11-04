from unittest.mock import patch, MagicMock
from listenbrainz.domain import metabrainz_notifications
from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class MetabrainNotificationsTestCase(NonAPIIntegrationTestCase):
    @patch("listenbrainz.domain.metabrainz_notifications.send_multiple_notifications")
    def test_send_notification(self, mock_send_multiple):
        metabrainz_notifications.send_notification(
            subject="test123",
            body="testbody456",
            musicbrainz_row_id=123,
            user_email="usermail@mail.com",
            from_addr="noreply@listenbrainz.org",
        )
        expected_notification = [
                {
                    "subject": "test123",
                    "body": "testbody456",
                    "user_id": 123,
                    "to": "usermail@mail.com",
                    "project": "listenbrainz",
                    "sent_from": "noreply@listenbrainz.org",
                    "reply_to": "noreply@listenbrainz.org",
                    "send_email": True,
                    "important": True,
                    "expire_age": 7,
                    "template_id": None,
                    "template_params": None
                }
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
        mock_response.json.return_value = {"notifications_enabled": True, "digest": True, "digest_age": 7}
        mock_get.return_value = mock_response

        result = metabrainz_notifications.get_notification_preference(musicbrainz_row_id=456)

        expected_url = "https://metabrainz.org/notification/456/notification-preference"
        mock_get.assert_called_once_with(
            url=expected_url, headers={"Authorization": "Bearer access_token"}
        )
        self.assertEqual(result, {"notifications_enabled": True, "digest": True, "digest_age": 7})

    @patch("listenbrainz.domain.metabrainz_notifications._fetch_token")
    @patch("requests.post")
    def test_set_digest_preference(self, mock_post, mock_fetch_token):
        mock_fetch_token.return_value = "access_token"
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"notifications_enabled": True, "digest": True, "digest_age": 14}
        mock_post.return_value = mock_response

        result = metabrainz_notifications.set_notification_preference(
            musicbrainz_row_id=789, notifications_enabled=True, digest=True, digest_age=14
        )

        expected_url = "https://metabrainz.org/notification/789/notification-preference"
        expected_data = {"notifications_enabled": True, "digest": True, "digest_age": 14}
        mock_post.assert_called_once_with(
            url=expected_url, json=expected_data, headers={"Authorization": "Bearer access_token"}
        )
        self.assertEqual(result, {"notifications_enabled": True, "digest": True, "digest_age": 14})
