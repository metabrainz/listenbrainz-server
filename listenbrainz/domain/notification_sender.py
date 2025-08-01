from requests.auth import HTTPBasicAuth
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from brainzutils import cache
from flask import current_app
import requests


TOKEN_CACHE_KEY = "notification_access_token"
# METABRAINZ_SEND_NOTIFICATIONS_URL = "https://metabrainz.org/notification/send"
METABRAINZ_SEND_NOTIFICATIONS_URL = "http://metabrainz-web-1:8000/notification/send"


def send_notification(
    subject: str,
    body: str,
    user_id: int,
    user_email: str,
    from_addr: str,
    project: str = "listenbrainz",
    send_email: bool = True,
    important: bool = True,
    expire_age: int = 7,
):
    """Function to send a single notification.
    This function prepares a single notification and uses `send_multiple_notifications` to send it.

    Args:
        ``subject``
        ``body``
        ``userid``
        ``user_email``
        ``from_addr``
        ``project``
        ``send_email``
        ``important``
        ``expire_age``

    Raises:
        A HTTPError if there's a failure.

    """

    notification = [
        {
            "subject": subject,
            "body": body,
            "user_id": user_id,
            "to": user_email,
            "project": project,
            "sent_from": from_addr,
            "send_email": send_email,
            "important": important,
            "expire_age": expire_age,
        }
    ]

    send_multiple_notifications([notification])


def send_multiple_notifications(notifications: list[dict]):
    """Function to send bulk notifications.

    Args:
        ``notifications``: A list of notification dictionaries to be sent.

    Raises:
        A HTTPError if there's a failure.

    """

    token = _fetch_token()
    tokenized_url = METABRAINZ_SEND_NOTIFICATIONS_URL + f"?token={token}"

    response = requests.post(url=tokenized_url, json=notifications)
    response.raise_for_status()


def _fetch_token() -> str:
    """Helper function to fetch OAuth2 token from redis cache, If no token is found or it's expired, a new token is requested."""

    token = cache.get(TOKEN_CACHE_KEY)
    if token is not None:
        return token

    client_id = current_app.config["OAUTH_CLIENT_ID"]
    client_secret = current_app.config["OAUTH_CLIENT_SECRET"]
    token_url = current_app.config["OAUTH_TOKEN_URL"]

    client = BackendApplicationClient(client_id=client_id, scope="notification")
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url=token_url, auth=HTTPBasicAuth(client_id, client_secret)
    )
    access_token = token["access_token"]
    expires_in = token["expires_in"]

    cache.set(key=TOKEN_CACHE_KEY, val=access_token, expirein=expires_in)
    return access_token
