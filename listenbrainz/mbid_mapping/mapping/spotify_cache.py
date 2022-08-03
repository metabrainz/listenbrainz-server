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

    def __init__(self):
        self.id_queue = UniqueQueue()
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
                            self.id_queue.put("artist:%s" % track_artist["id"])

            album["tracks"] = tracks

        artist["albums"] = albums

        return artist

    def fetch_artist_ids_from_track_id(self, track_id):
        return [a["id"] for a in self.sp.track(track_id)["artists"]]

    def insert_artist(self, artist):
        artist["_id"] = artist["id"]
        artist["fetched"] = datetime.utcnow().isoformat()
        artist["expires"] = (datetime.utcnow() + timedelta(days=self.CACHE_TIME)).isoformat()
        artist["status"] = "fetched"
        couchdb.insert_data(self.COUCHDB_NAME, [artist])

    def add_pending_spotify_ids(self, spotify_ids):
        for spotify_id in spotify_ids:
            if not spotify_id.startswith("artist:") and not spotify_id.startswith("track:"):
                print("Invalid ID submitted -- all IDs must start with artist: or track:")
                return

        data = {"status": "pending",
                          "_id": str(uuid.uuid4()),
                          "spotify_ids": spotify_ids,
                          "queued": datetime.utcnow().isoformat()}
        couchdb.insert_data(self.COUCHDB_NAME, [data])

    def load_ids_to_process(self):
        mango = {"selector": {"status": "pending"},
                 "fields": ["queued", "spotify_ids"],
                 "sort": [{"queued": "asc"}]}
        ret = False
        for row in couchdb.find_data(self.COUCHDB_NAME, mango):
            for spotify_id in row["spotify_ids"]:
                print("Add spotify id %s to queue" % spotify_id)
                self.id_queue.put(spotify_id)
                ret = True

        return ret

    def process_artist(self, artist_id):

        print(f"Process {artist_id}")

        # Fetch an existing doc and if found, see if it has expired
        existing_doc = couchdb.get(self.COUCHDB_NAME, artist_id)
        if existing_doc is not None:
            expires = dateutil.parser.isoparse(existing_doc["expires"])
            if dateutil.parser.isoparse(existing_doc["expires"]) > datetime.utcnow():
                print("Find existing doc!")
                return
            rev = int(existing_doc["_rev"]) + 1
        else:
            rev = 1

        artist_data = self.fetch_artist(artist_id)
        artist_data["_rev"] = str(rev)

        self.insert_artist(artist_data)

    def start(self):
        """ Main loop of the application """

        while True:
            # If we have no more artists in the queue, fetch from the DB. If there are none, sleep, try again.
            if self.id_queue.empty():
                if not self.load_ids_to_process():
                    sleep(60)
                    continue

            spotify_id = self.id_queue.get()
            print(f"got {spotify_id}")

            if spotify_id.startswith("track:"):
                artist_ids = self.fetch_artist_ids_from_track_id(spotify_id[6:])
            elif spotify_id.startswith("artist:"):
                artist_ids = [spotify_id[7:]]
            else:
                raise ValueError("Unknown ID type", spotify_id)

            for artist_id in artist_ids:
                self.process_artist(artist_id)

            print("%d items in queue." % self.id_queue.size())


def run_spotify_metadata_cache():
    smc = SpotifyMetadataCache()
    smc.start()


def queue_spotify_ids(spotify_ids):
    smc = SpotifyMetadataCache()
    smc.add_pending_spotify_ids(spotify_ids)
