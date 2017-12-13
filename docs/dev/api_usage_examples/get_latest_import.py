'''
get_latest_import.py
'''

import requests

ROOT = '127.0.0.1'
TOKEN = 'YOUR_TOKEN_HERE'
USERNAME = 'YOUR_USERNAME_HERE' # Replace with the username from which you got the token above.
AUTH_HEADER = {
    "Authorization": "Token {0}".format(TOKEN)
}

# The AUTH_HEADER token can be any valid token.
def get_latest_import(username):
    """Gets the latest import timestamp of a given user.

    Args:
        username: User to get latest import time of.

    Returns:
        A Unix timestamp if there's an OK status.

    Raises:
        An HTTPError if there's a failure.
        A ValueError if the JSON in the response is invalid.
        An IndexError if the JSON is not structured as expected.
    """
    response = requests.get(
        url="http://{0}/1/latest-import".format(ROOT),
        params={
            "user_name": username
        },
        headers=AUTH_HEADER
    )

    response.raise_for_status()

    return response.json()["latest_import"]

if __name__ == "__main__":
    timestamp = get_latest_import(USERNAME)

    print("User {0} last imported on {1}".format(USERNAME, timestamp))
