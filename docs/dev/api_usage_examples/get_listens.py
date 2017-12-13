'''
get_listens.py
'''

import requests

ROOT = '127.0.0.1'
TOKEN = 'YOUR_TOKEN_HERE'
USERNAME = 'YOUR_USERNAME_HERE' # Replace with the username from which you got the token above.
AUTH_HEADER = {
    "Authorization": "Token {0}".format(TOKEN)
}

# The token in AUTH-HEADER must be valid, but it doesn't have to be the token of the user you're
# trying to get the listen history of.
def get_listens(username, min_ts=None, max_ts=None, count=None):
    """Gets the listen history of a given user.

    Args:
        username: User to get listen history of.
        min_ts: History before this timestamp will not be returned.
                DO NOT USE WITH max_ts.
        max_ts: History after this timestamp will not be returned.
                DO NOT USE WITH min_ts.
        count: How many listens to return. If not specified,
               uses a default from the server.

    Returns:
        A list of listen info dictionaries if there's an OK status.

    Raises:
        An HTTPError if there's a failure.
        A ValueError if the JSON in the response is invalid.
        An IndexError if the JSON is not structured as expected.
    """
    response = requests.get(
        url="http://{0}/1/user/{1}/listens".format(ROOT, username),
        params={
            "min_ts": min_ts,
            "max_ts": max_ts,
            "count": count
        },
        headers=AUTH_HEADER
    )

    response.raise_for_status()

    return response.json()['payload']['listens']

if __name__ == "__main__":
    listens = get_listens(USERNAME)

    for track in listens:
        print("Track: {0}, listened at {1}".format(track["track_metadata"]["track_name"],
                                                   track.get("listened_at", "unknown")))
