#!/usr/bin/env python3
from datetime import datetime, timedelta
import json
from queue import Queue

import couchdb
import spotipy
import dateutil.parser
from spotipy.oauth2 import SpotifyClientCredentials

import config

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


class SpotifyMetadataCache():

    COUCHDB_NAME = "spotify-metadata-cache"
    CACHE_TIME = 180  # days

    def __init__(self):
        self.id_queue = UniqueQueue()
        self.seen_ids = {}
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=config.SPOTIFY_APP_CLIENT_ID,
                                                                        client_secret=config.SPOTIFY_APP_CLIENT_SECRET))
        self.couch = couchdb.Server('http://listenbrainz:listenbrainz@localhost:5984/')
        try:
            self.db = self.couch[self.COUCHDB_NAME]
        except couchdb.http.ResourceNotFound:
            self.create_db()
            self.db = self.couch[self.COUCHDB_NAME]

    def create_db(self):
        self.couch.create(self.COUCHDB_NAME)

    def queue_id(self, spotify_id):
        self.id_queue.put(spotify_id)

    def fetch_artist(self, artist_id):
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

            for track in tracks:
                for track_artist in track["artists"]:
                    if track_artist["id"] != artist_id and track_artist["id"] not in self.seen_ids:
                        self.id_queue.put("artist:%s" % track_artist["id"])

            album["tracks"] = tracks

        artist["albums"] = albums

        return artist

    def fetch_artist_ids_from_track_id(self, track_id):
        return [ a["id"] for a in self.sp.track(track_id)["artists"] ]

    def insert_artist(self, artist, exists=False):
        artist["_id"] = artist["id"]
        artist["fetched"] = datetime.utcnow().isoformat()
        artist["expires"] = (datetime.utcnow() + timedelta(days=self.CACHE_TIME)).isoformat()
        if exists:
            self.db.update([artist])
        else:
            self.db.save(artist)
        print("Inserted artist '%s' %s" % (artist["name"], artist["id"]))

    def process_artist(self, artist_id):

        # Check our internal cache if we've seen it recently
        if artist_id in self.seen_ids:
            return

        # Mark this ID as recently seen
        self.seen_ids[artist_id] = datetime.now()

        # Fetch an existing doc and if found, see if it has expired
        existing_doc = self.db.get(artist_id)
        if existing_doc is not None:
            expires = dateutil.parser.isoparse(existing_doc["expires"])
            if dateutil.parser.isoparse(existing_doc["expires"]) > datetime.utcnow():
                print("Artist '%s' in db, not stale. Skipping." % artist_id)
                return
            else:
                print("Artist '%s' in db, stale. Fetch new." % artist_id)

        artist_data = self.fetch_artist(artist_id)

        self.insert_artist(artist_data, existing_doc is not None)

    def start(self):
        """ Main loop of the application """

        while True:
            spotify_id = self.id_queue.get()

            # Check to see if we've recently queried this id, if so move to the next id
            if spotify_id in self.seen_ids:
                continue

            if spotify_id.startswith("track:"):
                artist_ids = self.fetch_artist_ids_from_track_id(spotify_id[6:])
            elif spotify_id.startswith("artist:"):
                artist_ids = [ spotify_id[7:] ]
            else:
                raise ValueError("Unknown ID type", spotify_id)

            for artist_id in artist_ids:
                self.process_artist(artist_id)

            print("%d items in queue." % self.id_queue.size())


def run_spotify_metadata_cache():
    smc = SpotifyMetadataCache()
    smc.queue_id("artist:6liAMWkVf5LH7YR9yfFy1Y")
    smc.queue_id("track:5wdub8zu2WLds6uRN0jUsV")
    smc.start()
