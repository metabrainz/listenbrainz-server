#!/usr/bin/env python3

import json
from operator import itemgetter
import os
import time
import sys

import click
import pysolr
from solrq import Q
from icecream import ic
import requests
from fuzzywuzzy.fuzz import partial_ratio as fuzzy


SOLR_HOST = "localhost"
SOLR_PORT = 8983
SOLR_CORE = "release-index"

LISTENBRAINZ_HOST = "https://api.listenbrainz.org"

MIN_NUMBER_OF_RECORDINGS = 3

def solr_search(artist, release, recordings, track_count=None, debug=False):

    query = {"title": release,
             "ac_name": artist,
             "recording_names": recordings}

    if type(track_count) is int: 
         query["count"] = track_count

    solr = pysolr.Solr('http://%s:%d/solr/%s' % (SOLR_HOST, SOLR_PORT, SOLR_CORE), always_commit=True)
    docs = solr.search(Q(**query), fl="*,score") # , debug="true")
    for doc in docs:
        if debug:
            print(docs.debug["explain"][doc["id"]])
        if type(track_count) is int and int(doc['count'][0]) != track_count:
            continue

        print("  %s %8s %.3f %-30s %-30s" % (doc['id'], doc['rank'][0], doc['score'], doc['title'][0], doc['ac_name'][0]))


ACCEPT_THRESHOLD = 85
def lookup_album_on_solr(lb_release, debug=False):

    query = {"title": lb_release["release_name"],
             "ac_name": lb_release["artist_credit_name"],
             "recording_names": lb_release["recordings"] }

    solr = pysolr.Solr('http://%s:%d/solr/%s' % (SOLR_HOST, SOLR_PORT, SOLR_CORE), always_commit=True)
    docs = solr.search(Q(**query), fl="*,score", debug="true")

    saved_docs = []
    last_score = None
    for doc in docs:
        recording_names = doc['recording_names'][0].split("\n") 
        mb_release = { "artist_credit_name": doc['ac_name'][0],
                       "release_name": doc['title'][0],
                       "recordings": recording_names,
                       "rank": doc["rank"][0] }
        score, reject = fuzzy_release_compare(mb_release, lb_release, True)
        doc["fuzzy"] = score
        if not last_score:
            last_score = score

        if score < ACCEPT_THRESHOLD or score < last_score:
            break

        if reject:
            continue

        saved_docs.append(doc)

    if not saved_docs:
        return None

    return sorted(saved_docs, key=itemgetter("rank"))[0]



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

    rel = { "artist_credit_name": release["artist_credit_name"],
            "release_name": release["release_name"],
            "recordings" : recording_names }

    return lookup_album_on_solr(rel)


def load_listens_for_user(user_name, ts=None):

    if ts is None:
        ts = int(time.time())

    r = requests.get("%s/1/user/%s/listens" % (LISTENBRAINZ_HOST, user_name), params={'max_ts':ts, "count": 100})
    if r.status_code != 200:
        print("Failed to fetch Listens")
        return []

    return r.json()["payload"]["listens"]


def listenbrainz_release_filter(user_name):

# TODO: Check if artist varies too much
#       Check if a track is just on repeat
    listens = []
    ts = int(time.time())

    last_artist = ""
    last_release = ""
    tracks = []
    for i in range(5):
        listens = load_listens_for_user("rob", ts)
        for listen in listens:
            artist = listen["track_metadata"]["artist_name"]
            release = listen["track_metadata"]["release_name"]
            if (last_release and release != last_release):
                if len(tracks) >= MIN_NUMBER_OF_RECORDINGS:
                    recording_names = []
                    recording_artists = []
                    tracks.reverse()
                    for i, track in enumerate(tracks):
                        recording_names.append("%d %s " % (i+1, track["track_metadata"]["track_name"].replace("\n", " ")))
                        recording_artists.append(track["track_metadata"]["artist_name"])


                    rel = { "artist_credit_name": last_artist,
                            "release_name": last_release,
                            "recordings" : recording_names,
                            "recording_artists": recording_artists }
                    solr_doc = lookup_album_on_solr(rel, True)
                    if solr_doc:
                        print("Accepted fuzzy score: %d rank %s\n" % (solr_doc["fuzzy"], solr_doc["rank"][0]))

                tracks = []
            
            tracks.append(listen)

            last_artist = artist
            last_release = release
            ts = listen["listened_at"]


MINIMUM_TRACK_MATCH = 60
def fuzzy_release_compare(mb_release, lb_release, debug=False):

# TODO: unaccent

    artist_weight = .17
    release_weight = .17
    recordings_weight = .4
    recording_count_weight = .26

    artist_score = fuzzy(mb_release["artist_credit_name"].lower(), lb_release["artist_credit_name"].lower())
    release_score = fuzzy(mb_release["release_name"].lower(), lb_release["release_name"].lower())
    if len(lb_release["recordings"]) < len(mb_release["recordings"]):
        recording_count_score = 100.0 * len(lb_release["recordings"]) / len(mb_release["recordings"])
    else:
        recording_count_score = 100.0 * (len(mb_release["recordings"]) / len(lb_release["recordings"]))

    if debug:
        print("%3d %-40s %-40s" % (artist_score, mb_release["artist_credit_name"][:39], lb_release["artist_credit_name"][:39]))
        print("%3d %-40s %-40s" % (release_score, mb_release["release_name"][:39], lb_release["release_name"][:39]))

    recording_score = 0.0
    count = 0
    reject = False
    for mb_track, lb_track, lb_artist in zip(mb_release["recordings"], lb_release["recordings"], lb_release["recording_artists"]):
        score = fuzzy(mb_track.lower(), lb_track.lower())
        if score < MINIMUM_TRACK_MATCH:
            reject = True

        count += 1
        if debug:
            print("    %3d %-40s %-40s %-40s" % (score, mb_track[:39], lb_track[:39], lb_artist))
        recording_score += score

    recording_score /= count
    if debug:
        print("%3d %d tracks                                %d tracks" % (recording_count_score, len(mb_release["recordings"]), len(lb_release["recordings"])))

    score = (artist_score * artist_weight) + (release_score * release_weight) + \
                (recording_count_score * recording_count_weight) + (recording_score * recordings_weight)
    if debug:
        print("%3d total, rank %s" % (score, mb_release["rank"]), end='')

    if reject:
        print(" *** REJECT!", end="")

    print("\n")

    return (score, reject)


def load_and_fuzzy_release_compare(mb_release_id, lb_release_id, debug=True):
    with open(os.path.join("test", mb_release_id + ".json"), "r") as f:
        mb_release = json.loads(f.read())
    with open(os.path.join("test", lb_release_id + ".json"), "r") as f:
        lb_release = json.loads(f.read())

    return fuzzy_release_compare(mb_release, lb_release, debug)


def test_compare_releases():
    load_and_fuzzy_release_compare("48313c92-c8a6-47c5-91e3-87d514419135", "7e5d3746-210d-439c-8711-d8d700ac7ae3")
    load_and_fuzzy_release_compare("7e5d3746-210d-439c-8711-d8d700ac7ae3", "7e5d3746-210d-439c-8711-d8d700ac7ae3")
    load_and_fuzzy_release_compare("7c08b5f8-2d6f-4d72-a829-3175528ef25f", "7e5d3746-210d-439c-8711-d8d700ac7ae3")


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

@cli.command()
def test():
    test_compare_releases()

def usage(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == "__main__":
    cli()
    sys.exit(0)
