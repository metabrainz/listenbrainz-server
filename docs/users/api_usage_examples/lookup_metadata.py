#!/usr/bin/env python3

import json
import requests

# Set DEBUG to True to test local dev server.
DEBUG = False
ROOT = 'http://localhost:8100' if DEBUG else 'https://api.listenbrainz.org'

def lookup_metadata(track_name: str, artist_name: str, incs: str) -> dict:
    """Looks up the metadata for a listen using track name and artist name."""
    params = {
        "recording_name": track_name,
        "artist_name": artist_name
    }
    if incs:
        params["metadata"] = True
        params["incs"] = incs
    response = requests.get(
        url="{0}/1/metadata/lookup/".format(ROOT),
        params=params
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    track_name = input('Please input the track name of the listen: ').strip()
    artist_name = input('Please input the artist name of the listen: ').strip()
    incs = input('Please input extra metadata to include (leave empty if not desired): ').strip()

    metadata = lookup_metadata(track_name, artist_name, incs)

    print()
    if metadata:
        print("Metadata found.")
        print(json.dumps(metadata, indent=4))
    else:
        print("No metadata found.")
