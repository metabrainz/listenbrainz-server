import traceback
from datetime import datetime, timedelta
from queue import Queue, Empty
from time import monotonic, sleep
import threading

import spotipy
import ujson
import urllib3
from spotipy import SpotifyClientCredentials
from sqlalchemy import text

from listenbrainz.db import timescale
from listenbrainz.utils import init_cache
from brainzutils import metrics, cache

UPDATE_INTERVAL = 30
CACHE_TIME = 180


class UniqueQueue(object):
    def __init__(self):
        self.queue = Queue()
        self.set = set()

    def put(self, d):
        if d not in self.set:
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


class SpotifyIdsQueue(threading.Thread):
    """ This class coordinates incoming listens and legacy listens, giving
        priority to new and incoming listens. Threads are fired off as needed
        looking up jobs in the background and then this main matcher
        thread can deal with the statstics and reporting"""

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.done = False
        self.app = app
        self.queue = UniqueQueue()

        self.retry = urllib3.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            respect_retry_after_header=False
        )
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=app.config["SPOTIFY_CLIENT_ID"],
            client_secret=app.config["SPOTIFY_CLIENT_SECRET"])
        )

        init_cache(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'],
                   namespace=app.config['REDIS_NAMESPACE'])
        metrics.init("listenbrainz")

    def add_spotify_ids(self, ids):
        for spotify_id in ids:
            spotify_id = spotify_id.split("/")[-1]
            self.queue.put(spotify_id)

    def terminate(self):
        self.done = True
        self.join()

    def update_metrics(self, stats):
        """ Calculate stats and self.app.logger.info status to stdout and report metrics."""
        # metrics.set("listenbrainz-spotify-metadata-cache", )

    def fetch_artist(self, artist_id):
        self.app.logger.info("Fetch artist")
        artist = self.sp.artist(artist_id)

        self.app.logger.info("Fetch albums")
        results = self.sp.artist_albums(artist_id, album_type='album,single,compilation')
        albums = results.get('items')
        if not albums:
            return artist

        while results.get('next'):
            results = self.sp.next(results)
            if results.get('items'):
                albums.extend(results.get('items'))

        self.app.logger.info("Fetch tracks")
        for album in albums:
            results = self.sp.album_tracks(album["id"], limit=50)
            tracks = results.get("items")
            if not tracks:
                return artist
            while results.get("next"):
                results = self.sp.next(results)
                if results.get("items"):
                    tracks.extend(results.get("items"))

            for track in tracks:
                for track_artist in track.get("artists"):
                    if track_artist["id"] != artist_id and track_artist["id"]:
                        self.queue.put("artist:%s" % track_artist["id"])

            album["tracks"] = tracks

        artist["albums"] = albums
        self.app.logger.info("Fetch artist complete")

        return artist

    def insert_artist(self, spotify_id, data):
        last_fetched = datetime.utcnow()
        expires_at = datetime.utcnow() + timedelta(days=CACHE_TIME)
        with timescale.engine.begin() as ts_conn:
            query = """
                INSERT INTO mapping.spotify_metadata_cache (spotify_id, data, dirty, last_fetched, expires_at)
                     VALUES (:spotify_id, :data, 'f', :last_fetched, :expires_at)
                ON CONFLICT (spotify_id)
                  DO UPDATE SET
                            data = EXCLUDED.data
                          , last_fetched = EXCLUDED.last_fetched
                          , expires_at = EXCLUDED.expires_at
                          , dirty = 'f'
            """
            ts_conn.execute(text(query), {
                "spotify_id": spotify_id,
                "data": ujson.dumps(data),
                "last_fetched": last_fetched,
                "expires_at": expires_at
            })
        
        cache_key = "spotify:" + spotify_id
        cache.set(cache_key, 1, expirein=0)
        cache.expireat(cache_key, int(expires_at.timestamp()))

    def process_spotify_id(self, spotify_id):
        cache_key = "spotify:" + spotify_id
        if cache.get(cache_key) is not None:
            return
        
        self.app.logger.info(f"{spotify_id}: ", end="")
        artist_data = self.fetch_artist(spotify_id)
        self.insert_artist(spotify_id, artist_data)

    def run(self):
        """ main thread entry point"""
        stats = {}

        # the main thread loop
        update_time = monotonic() + UPDATE_INTERVAL
        try:
            with self.app.app_context():
                while not self.done:
                    try:
                        spotify_id = self.queue.get()
                        self.process_spotify_id(spotify_id)
                    except Empty:
                        sleep(5)
                        continue

                    if monotonic() > update_time:
                        update_time = monotonic() + UPDATE_INTERVAL
                        self.update_metrics(stats)
        except Exception:
            self.app.logger.info(traceback.format_exc())

        self.app.logger.info("job queue thread finished")
