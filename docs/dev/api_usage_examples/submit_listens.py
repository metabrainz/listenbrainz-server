'''
submit_listens.py
'''

from time import time
from enum import Enum
import requests

ROOT = '127.0.0.1'
TOKEN = 'YOUR_TOKEN_HERE'
AUTH_HEADER = {
    "Authorization": "Token {0}".format(TOKEN)
}

# The token in AUTH-HEADER must be the token of the user you're submitting listens for.
def submit_listen(listen_type, payload):
    """Submits listens for the track(s) in payload.

    Args:
        listen_type: One type from the ListenType enum.
        payload: A list of Track dictionaries.

    Returns:
         The json response if there's an OK status.

    Raises:
         An HTTPError if there's a failure.
         A ValueError is the JSON in the response is invalid.
    """

    response = requests.post(
        url="http://{0}/1/submit-listens".format(ROOT),
        json={
            "listen_type": listen_type.value,
            "payload": payload
        },
        headers=AUTH_HEADER
    )

    response.raise_for_status()

    return response.json()

class ListenType(Enum):
    Single = "single"
    Playing = "playing_now"
    Import = "import"

if __name__ == "__main__":
    EXAMPLE_PAYLOAD = [
        {
            # An example track.
            "listened_at": int(time()),
            "track_metadata": {
                "additional_info": {
                    "release_mbid": "bf9e91ea-8029-4a04-a26a-224e00a83266",
                    "artist_mbids": [
                        "db92a151-1ac2-438b-bc43-b82e149ddd50"
                    ],
                    "recording_mbid": "98255a8c-017a-4bc7-8dd6-1fa36124572b",
                    "tags": ["you", "just", "got", "semi", "rick", "rolled"]
                },
                "artist_name": "Rick Astley",
                "track_name": "Never Gonna Give You Up",
                "release_name": "Whenever you need somebody"
            }
        }
    ]

    json_response = submit_listen(listen_type=ListenType.Single, payload=EXAMPLE_PAYLOAD)

    print("Response was: {0}".format(json_response))
    print("Check your listens - there should be a Never Gonna Give You Up track, played recently.")
