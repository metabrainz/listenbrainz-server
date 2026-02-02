#!/usr/bin/env python3

import requests

# Set DEBUG to True to test local dev server.
# API keys for local dev server and the real server are different.
DEBUG = True
ROOT = 'http://localhost:8100' if DEBUG else 'https://api.listenbrainz.org'

def submit_feedback(token: str, recording_mbid: str, score: int):
    """ Submit feedback for recording. """
    response = requests.post(
        url="{0}/1/feedback/recording-feedback".format(ROOT),
        json={"recording_mbid": recording_mbid, "score": score},
        headers={"Authorization": f"Token {token}"}
    )
    response.raise_for_status()
    print("Feedback submitted.")


if __name__ == "__main__":
    recording_mbid = input('Please input the recording mbid of the listen: ').strip()
    score = int(input('Please input the feedback score (1, 0 or -1): ').strip())
    token = input('Please enter your auth token: ').strip()

    submit_feedback(token, recording_mbid, score)
