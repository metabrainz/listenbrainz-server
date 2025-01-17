from time import time
import requests

# Set DEBUG to True to test local dev server.
# API keys for local dev server and the real server are different.
DEBUG = True
ROOT = 'http://localhost:8100' if DEBUG else 'https://api.listenbrainz.org'


def set_latest_import(timestamp, token, service="librefm"):
    """Sets the time of the latest import.

    Args:
        timestamp: Unix epoch to set latest import to.
        token: the auth token of the user you're setting latest_import of
        service: service to set latest import time of.

    Returns:
        The JSON response if there's an OK status.

    Raises:
        An HTTPError if there's a failure.
        A ValueError if the JSON response is invalid.
    """
    response = requests.post(
        url="{0}/1/latest-import".format(ROOT),
        json={
            "ts": timestamp,
            "service": service
        },
        headers={
            "Authorization": "Token {0}".format(token),
        }
    )

    response.raise_for_status()

    return response.json()

if __name__ == "__main__":
    ts = int(time())
    token = input('Please enter your auth token: ')
    json_response = set_latest_import(ts, token)

    print("Response was: {0}".format(json_response))
    print("Set latest import time to {0}.".format(ts))
