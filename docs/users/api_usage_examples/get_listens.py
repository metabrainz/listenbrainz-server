import requests

# Set DEBUG to True to test local dev server.
# API keys for local dev server and the real server are different.
DEBUG = True
ROOT = 'http://localhost:8100' if DEBUG else 'https://api.listenbrainz.org'

# The following token must be valid, but it doesn't have to be the token of the user you're
# trying to get the listen history of.
TOKEN = 'YOUR_TOKEN_HERE'
AUTH_HEADER = {
    "Authorization": "Token {0}".format(TOKEN)
}


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
               This does not guarantee all requested listens will be returned.


    Returns:
        A list of listen info dictionaries if there's an OK status.
        The response will contain a count and a search_status which indicates
        whether the database search ended before all requested listens were returned.
        This object has the following shape:

        .. code-block:: text

            {
                "partial": <boolean>,
                "continue_max_ts": <unix timestamp, optional>,
                "continue_min_ts": <unix timestamp, optional>
            }

        ``partial`` is always present. When true, either ``continue_max_ts`` and ``continue_min_ts``
        will be present to continue the search.

    Raises:
        An HTTPError if there's a failure.
        A ValueError if the JSON in the response is invalid.
        An IndexError if the JSON is not structured as expected.
    """
    response = requests.get(
        url="{0}/1/user/{1}/listens".format(ROOT, username),
        params={
            "min_ts": min_ts,
            "max_ts": max_ts,
            "count": count,
        },
        # Note that an authorization header isn't compulsary for requests to get listens
        # BUT requests with authorization headers are given relaxed rate limits by ListenBrainz
        headers=AUTH_HEADER,
    )

    response.raise_for_status()

    return response.json()['payload']['listens']

if __name__ == "__main__":
    username = input('Please input the MusicBrainz ID of the user: ')
    listens = get_listens(username)

    for track in listens:
        print("Track: {0}, listened at {1}".format(track["track_metadata"]["track_name"],
                                                   track["listened_at"]))
