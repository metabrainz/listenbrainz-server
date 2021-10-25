#!/usr/bin/env python3

import sys
from time import time, sleep
from uuid import uuid4
from random import randint

import click
import requests

ROOT = 'https://api.listenbrainz.org'
ROOT = 'http://localhost'


def submit_listen(url, listen_type, payload, token):
    """Submits listens for the track(s) in payload.

    Args:
        listen_type (str): either of 'single', 'import' or 'playing_now'
        payload: A list of Track dictionaries.
        token: the auth token of the user you're submitting listens for

    Returns:
         The json response if there's an OK status.

    Raises:
         An HTTPError if there's a failure.
         A ValueError is the JSON in the response is invalid.
    """

    response = requests.post(
        url="{0}/1/submit-listens".format(url),
        json={
            "listen_type": listen_type,
            "payload": payload,
        },
        headers={
            "Authorization": "Token {0}".format(token)
        }
    )
    response.raise_for_status()


@click.command()
@click.option('--url', '-u', help="Host to submit to. default: http://localhost", default="http://localhost")
@click.argument('token', nargs=1)
@click.argument('release', nargs=1)
def submit_release(token, release, url):
    """ Fetch a release from MusicBrainz and submit it as listens to LB

        Arguments:
           User token from user profile page
           MusicBrainz release MBID to fetch and submit
    """

    resp = requests.get(
        "https://musicbrainz.org/ws/2/release/%s?inc=recordings+artists&fmt=json" % release)
    if resp.status_code != 200:
        print("Failed to fetch album: %d" % resp.code)
        sys.exit(-1)

    jdata = resp.json()
    artist = jdata["artist-credit"][0]["artist"]["name"]
    recordings = jdata['media'][0]['tracks']

    time_index = int(time())
    for rec in recordings:
        time_index -= int(rec["length"]) // 1000
        payload = [
            {
                "listened_at": time_index,
                "track_metadata": {
                    "artist_name": artist,
                    "track_name": rec['title']
                }
            }
        ]
        try:
            submit_listen(url=url, listen_type='single',
                          payload=payload, token=token)
        except requests.exceptions.ConnectionError as err:
            print("Cannot connect to server: %s" % str(err))
            sys.exit(0)
        except requests.exceptions.HTTPError as err:
            print("Cannot submit listen. Is your user token correct?\n%s" % str(err))
            sys.exit(0)

        sleep(.2)

    sys.exit(0)


def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == '__main__':
    submit_release()
