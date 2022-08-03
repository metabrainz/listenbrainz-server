#!/usr/bin/env python3
from datetime import datetime, timedelta
from time import sleep
import json
from queue import Queue
import uuid

import spotipy
import dateutil.parser
from spotipy.oauth2 import SpotifyClientCredentials

from listenbrainz.db import couchdb
import config
from icecream import ic


class UniqueQueue(object):
    def __init__(self):
        self.queue = Queue()
        self.set = set()

    def put(self, d):
        if not d in self.set:
            self.queue.put(d)
            self.set.add(d)
            return True
        return False

    def get(self):
        d = self.queue.get()
        self.set.remove(d)
        return d

    def size(self):
        return self.queue.qsize()

    def empty(self):
        return self.queue.empty()


class SpotifyMetadataCache():

    COUCHDB_NAME = "spotify-metadata-cache"
    CACHE_TIME = 180  # days
    MAX_CACHED_PENDING_IDS = 1000

    def __init__(self):
        self.id_queue = UniqueQueue()
        self.pending_ids = []
        self.recent_ids = {}
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=config.SPOTIFY_APP_CLIENT_ID,
                                                                        client_secret=config.SPOTIFY_APP_CLIENT_SECRET))
        self.couch = couchdb.init(config.COUCHDB_USER, config.COUCHDB_PASSWORD, config.COUCHDB_HOST, config.COUCHDB_PORT)
        dbs = couchdb.list_databases("")
        if self.COUCHDB_NAME not in dbs:
            couchdb.create_database(self.COUCHDB_NAME)
        couchdb.create_index(self.COUCHDB_NAME, {
            "index": {
                "fields": ["status", "queued"]
            },
            "name": "status-index",
            "type": "json"
        })

    def queue_id(self, spotify_id):
        self.id_queue.put(spotify_id)

    def fetch_artist(self, artist_id, add_discovered_artists=False):
        artist = self.sp.artist(artist_id)

        results = self.sp.artist_albums(artist_id, album_type='album,single,compilation')
        albums = results['items']
        while results['next']:
            results = self.sp.next(results)
            albums.extend(results['items'])

        for album in albums:
            results = self.sp.album_tracks(album["id"], limit=50)
            tracks = results["items"]
            while results["next"]:
                results = self.sp.next(results)
                tracks.extend(results["items"])

            if add_discovered_artists:
                for track in tracks:
                    for track_artist in track["artists"]:
                        if track_artist["id"] != artist_id and track_artist["id"]:
                            self.add_pending_spotify_ids(["artist:%s" % track_artist["id"]])

            album["tracks"] = tracks

        artist["albums"] = albums

        return artist

    def fetch_artist_ids_from_track_id(self, track_id):
        try:
            track = self.sp.track(track_id)
        except spotipy.exceptions.SpotifyException:
            return None

        return [a["id"] for a in track["artists"]]

    def insert_artist(self, artist):
        artist["_id"] = artist["id"]
        artist["fetched"] = datetime.utcnow().isoformat()
        artist["expires"] = (datetime.utcnow() + timedelta(days=self.CACHE_TIME)).isoformat()
        artist["status"] = "fetched"
        couchdb.insert_data(self.COUCHDB_NAME, [artist])

    def add_recent_id(self, spotify_id):
        """ Add a recent id and return true if it was added """
        if spotify_id not in self.recent_ids:
            self.recent_ids[spotify_id] = datetime.now()
            return True

        return False

    def add_pending_spotify_ids(self, spotify_ids):
        try:
            iter(spotify_ids)
        except TypeException:
            raise ValueError("Must pass an iterable.")

        to_add = []
        for spotify_id in spotify_ids:
            if not spotify_id.startswith("artist:") and not spotify_id.startswith("track:"):
                raise ValueError("Invalid ID submitted -- all IDs must start with artist: or track:")

            if self.add_recent_id(spotify_id):
                to_add.append(spotify_id)

        self.pending_ids.extend(to_add)
        if len(self.pending_ids) > self.MAX_CACHED_PENDING_IDS:
            self.flush_pending_ids()

    def flush_pending_ids(self):
        if len(self.pending_ids) == 0:
            return

        data = {"status": "pending",
                          "_id": str(uuid.uuid4()),
                          "spotify_ids": self.pending_ids,
                          "queued": datetime.utcnow().isoformat()}
        couchdb.insert_data(self.COUCHDB_NAME, [data])
        self.pending_ids = []

    def load_ids_to_process(self):
        mango = {"selector": {"status": "pending"},
                 "fields": ["queued", "spotify_ids", "_id"],
                 "sort": [{"queued": "asc"}]}
        ret = False
        for row in couchdb.find_data(self.COUCHDB_NAME, mango):
            for spotify_id in row["spotify_ids"]:
                self.id_queue.put(spotify_id)
                ret = True
            couchdb.delete_data(self.COUCHDB_NAME, row["_id"])
            break

        return ret

    def print_stats(self):
        print(" queued %d, pending %d" % (self.id_queue.size(), len(self.pending_ids)))

    def process_artist(self, artist_id):

        print(f"{artist_id}: ", end="")

        # Fetch an existing doc and if found, see if it has expired
        existing_doc = couchdb.get(self.COUCHDB_NAME, artist_id)
        if existing_doc is not None:
            expires = dateutil.parser.isoparse(existing_doc["expires"])
            if dateutil.parser.isoparse(existing_doc["expires"]) > datetime.utcnow():
                print("fresh. ", end="")
                self.print_stats()
                return
            print("stale", end="")
            rev = int(existing_doc["_rev"]) + 1
        else:
            rev = None

        artist_data = self.fetch_artist(artist_id, add_discovered_artists=True)
        if rev is not None:
            artist_data["_rev"] = str(rev)

        self.insert_artist(artist_data)
        self.add_recent_id(artist_id)

        print("fetched: %-30s " % (artist_data["name"][:29]), end="")
        self.print_stats()

    def start(self):
        """ Main loop of the application """

        while True:
            # If we have no more artists in the queue, fetch from the DB. If there are none, sleep, try again.
            if self.id_queue.empty():
                self.flush_pending_ids()
                if not self.load_ids_to_process():
                    sleep(60)
                    continue

            spotify_id = self.id_queue.get()

            if spotify_id.startswith("track:"):
                artist_ids = self.fetch_artist_ids_from_track_id(spotify_id[6:])
                if artist_ids is None:
                    continue

            elif spotify_id.startswith("artist:"):
                artist_ids = [spotify_id[7:]]
            else:
                raise ValueError("Unknown ID type", spotify_id)

            for artist_id in artist_ids:
                self.process_artist(artist_id)


def run_spotify_metadata_cache():
    smc = SpotifyMetadataCache()
    smc.start()


def queue_spotify_ids(spotify_ids):
    smc = SpotifyMetadataCache()
    smc.add_pending_spotify_ids(spotify_ids)
    smc.flush_pending_ids()


def load_spotify_ids_from_file(filename):
    smc = SpotifyMetadataCache()
    count = 0
    with open(filename, "r") as f:
        while True:
            spotify_id = f.readline()
            if not spotify_id:
                break

            spotify_id = spotify_id.strip()
            smc.add_pending_spotify_ids([spotify_id])
            count += 1

    smc.flush_pending_ids()
    print("%d ids inserted" % count)
