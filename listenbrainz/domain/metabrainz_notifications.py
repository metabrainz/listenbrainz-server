import requests
from brainzutils import cache
from flask import current_app
from oauthlib.oauth2 import BackendApplicationClient
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session

TOKEN_CACHE_KEY = "notification_access_token"
METABRAINZ_NOTIFICATIONS_ENDPOINT = "https://metabrainz.org/notification"


def send_notification(
    musicbrainz_row_id: int,
    user_email: str,
    subject: str = None,
    body: str = None,
    template_id: str = None,
    template_params: dict = None,
    from_addr: str = "ListenBrainz <noreply@listenbrainz.org>",
    reply_to: str = "ListenBrainz <noreply@listenbrainz.org>",
    project: str = "listenbrainz",
    send_email: bool = True,
    important: bool = True,
    expire_age: int = 7,
):
    """Function to send a single notification.
    This function prepares a single notification and uses `send_multiple_notifications` to send it.

    Args:
        musicbrainz_row_id: (int) Required.
        user_email: (str) Required.
        subject: (str) Required if plain text email. Defaults to None.
        body: (str) Required if plain text email. Defaults to None.
        template_id: (str) Required if HTML email. Defaults to None.
        teamplate_params: (dict) Required if HTML email. Defaults to None.
        from_addr: (str) Optional. Defaults to `ListenBrainz <noreply@listenbrainz.org>`.
        project: (str) Optional. Defaults to `listenbrainz`.
        send_email: (bool) Optional. Defaults to True.
        important: (bool) Optional. Defaults to True.
        expire_age: (int) Optional. Defaults to 7.

    Raises:
        A HTTPError if there's a failure.

    """

    notification = {
            "user_id": musicbrainz_row_id,
            "to": user_email,
            "subject": subject,
            "body": body,
            "template_id": template_id,
            "template_params": template_params,
            "project": project,
            "sent_from": from_addr,
            "reply_to": reply_to,
            "send_email": send_email,
            "important": important,
            "expire_age": expire_age,
        }

    send_multiple_notifications([notification])


def send_multiple_notifications(notifications: list[dict]):
    """Function to send bulk notifications.

    Args:
        ``notifications``: A list of notification dictionaries to be sent.

    Raises:
        A HTTPError if there's a failure.

    """

    token = _fetch_token()
    headers = {"Authorization": f"Bearer {token}"}
    notification_send_endpoint = METABRAINZ_NOTIFICATIONS_ENDPOINT + "/send"

    response = requests.post(url=notification_send_endpoint, json=notifications, headers=headers)
    response.raise_for_status()


def get_notification_preference(musicbrainz_row_id: int) -> dict:
    """Retrieves the current digest preference of a user.

    Args:
        ``musicbrainz_row_id`` (int)

    Returns:
        A dict containing
        ``notifications_enabled`` (bool): Whether e-mail notifications are enabled for the user.
        ``digest`` (bool): Whether digest is enabled for the user.
        ``digest_age`` (int): The digest_age set for the user.

    Raises:
        A HTTPError if there's a failure.

    """
    notification_preference_endpoint = (
        METABRAINZ_NOTIFICATIONS_ENDPOINT + f"/{musicbrainz_row_id}/notification-preference"
    )
    token = _fetch_token()
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url=notification_preference_endpoint, headers=headers)
    response.raise_for_status()

    return response.json()


def set_notification_preference(
    musicbrainz_row_id: int, notifications_enabled: bool, digest: bool, digest_age: int = None
) -> dict:
    """Sets the digest preference for a user.

    Args:
        ``musicbrainz_row_id`` (int)
        ``notifications_enabled`` (bool): Whether e-mail notifications are enabled for the user.
        ``digest`` (bool): Whether digest should be enabled.
        ``digest_age`` (int): The age in days for the digest. If set to None, MeB server defaults it to 7 days.

    Returns:
        A dict containing
        ``notifications_enabled`` (bool): Whether e-mail notifications are enabled for the user.
        ``digest`` (bool): Whether digest is enabled for the user.
        ``digest_age`` (int): The digest age set for the user.

    Raises:
        A HTTPError if there's a failure.

    """
    notification_preference_endpoint = (
        METABRAINZ_NOTIFICATIONS_ENDPOINT + f"/{musicbrainz_row_id}/notification-preference"
    )
    token = _fetch_token()
    headers = {"Authorization": f"Bearer {token}"}
    data = {"notifications_enabled": notifications_enabled, "digest": digest, "digest_age": digest_age}

    response = requests.post(url=notification_preference_endpoint, json=data, headers=headers)
    response.raise_for_status()

    return response.json()


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
    token = oauth.fetch_token(token_url=token_url, auth=HTTPBasicAuth(client_id, client_secret))
    access_token = token["access_token"]
    expires_in = token["expires_in"]

    cache.set(key=TOKEN_CACHE_KEY, val=access_token, expirein=expires_in)
    return access_token
