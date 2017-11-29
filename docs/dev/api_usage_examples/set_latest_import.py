'''
set_latest_import.py
'''

from time import time
import requests

ROOT = '127.0.0.1'
TOKEN = 'YOUR_TOKEN_HERE'
AUTH_HEADER = {
    "Authorization": "Token {0}".format(TOKEN)
}

# Token in AUTH_HEADER must be that of the user you're setting for.
def set_latest_import(timestamp):
    """Sets the time of the latest import.

    Args:
        timestamp: Unix epoch to set latest import to.

    Returns:
        The JSON response if there's an OK status.

    Raises:
        An HTTPError if there's a failure.
        A ValueError if the JSON response is invalid.
    """
    response = requests.post(
        url="http://{0}/1/latest-import".format(ROOT),
        json={
            "ts": timestamp
        },
        headers=AUTH_HEADER
    )

    response.raise_for_status()

    return response.json()

if __name__ == "__main__":
    epoch = int(time())
    json_response = set_latest_import(epoch)

    print("Response was: {0}".format(json_response))
    print("Set latest import time to {0}.".format(epoch))
