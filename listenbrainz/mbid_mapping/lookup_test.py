#!/usr/bin/env python3

import json
import os
import time
import sys

import click
import pysolr
from solrq import Q
from icecream import ic
import requests


SOLR_HOST = "localhost"
SOLR_PORT = 8983
SOLR_CORE = "release-index"

LISTENBRAINZ_HOST = "https://api.listenbrainz.org"

MIN_NUMBER_OF_RECORDINGS = 3

def lookup_album_on_solr(artist, release, recordings, track_count=None, debug=False):

    query = {"title": release,
             "ac_name": artist,
             "recording_names": recordings}

    if type(track_count) is int: 
         query["count"] = track_count

    solr = pysolr.Solr('http://%s:%d/solr/%s' % (SOLR_HOST, SOLR_PORT, SOLR_CORE), always_commit=True)
    docs = solr.search(Q(**query), fl="*,score", debug="true")
    for doc in docs:
        if debug:
            print(docs.debug["explain"][doc["id"]])
        if type(track_count) is int and int(doc['count'][0]) != track_count:
            continue

        print("  %s %8s %.3f %-30s %-30s" % (doc['id'], doc['rank'][0], doc['score'], doc['title'][0], doc['ac_name'][0]))


def musicbrainz_lookup(release_mbid):

    r = requests.get("https://musicbrainz.org/ws/2/release/%s?fmt=json&inc=recordings+artists" % release_mbid)
    if r.status_code != 200:
        print("Failed to fetch JSON from MB")
        return None

    release = r.json()
    medium = release["media"][0]

    recording_names = [track["title"] for track in medium["tracks"]]
    return { "artist_credit_name": release["artist-credit"][0]["name"],
             "release_name": release["title"],
             "recordings" : recording_names }


def musicbrainz_sanity_check(release_mbid):
    
    release = musicbrainz_lookup(release_mbid)
    recording_names = []
    for i, track in enumerate(release["recordings"]):
        recording_names.append("%d %s " % (i, track))

    return lookup_album_on_solr(release["artist_credit_name"], release["release_name"], recording_names, len(release["recordings"]))


def load_listens_for_user(user_name, ts=None):

    if ts is None:
        ts = int(time.time())

    r = requests.get("%s/1/user/%s/listens" % (LISTENBRAINZ_HOST, user_name), params={'max_ts':ts, "count": 100})
    if r.status_code != 200:
        print("Failed to fetch Listens")
        return []

    return r.json()["payload"]["listens"]


def listenbrainz_release_filter(user_name):

    listens = []
    ts = int(time.time())

    last_artist = ""
    last_release = ""
    tracks = []
    for i in range(2):
        listens = load_listens_for_user("rob", ts)
        for listen in listens:
            artist = listen["track_metadata"]["artist_name"]
            release = listen["track_metadata"]["release_name"]
            if (last_artist and artist != last_artist) or (last_release and release != last_release):
                if len(tracks) >= MIN_NUMBER_OF_RECORDINGS:
                    print("%s: %s" % (last_artist, last_release))
                    recording_names = []
                    for i, track in enumerate(tracks):
                        recording_names.append("%d %s " % (i, track["track_metadata"]["track_name"]))

                    lookup_album_on_solr(last_artist, last_release, recording_names)

                tracks = []
            else:
                tracks.append(listen)

            last_artist = artist
            last_release = release
            ts = listen["listened_at"]



@click.group()
def cli():
    pass

@cli.command()
@click.argument('release_mbid', nargs=1)
def fetch(release_mbid):
    rel = musicbrainz_lookup(release_mbid)
    print(json.dumps(rel, indent=4, sort_keys=True))

@cli.command()
@click.argument('release_mbid', nargs=1)
def check(release_mbid):
    musicbrainz_sanity_check(release_mbid)

@cli.command()
@click.argument('user_name', nargs=1)
def filter(user_name):
    listenbrainz_release_filter(user_name)

def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == "__main__":
    cli()
    sys.exit(0)
