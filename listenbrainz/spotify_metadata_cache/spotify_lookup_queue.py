import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import Empty, PriorityQueue
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

UPDATE_INTERVAL = 60  # in seconds
CACHE_TIME = 180  # in days

DISCOVERED_ALBUM_PRIORITY = 1
INCOMING_ALBUM_PRIORITY = 0

CACHE_KEY_PREFIX = "spotify:album:"


@dataclass(order=True, eq=True, frozen=True)
class JobItem:
    priority: int
    spotify_id: str = field(compare=False)


class UniqueQueue:
    def __init__(self):
        self.queue = PriorityQueue()
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
        self.discovered_artists = set()

        self.retry = urllib3.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            respect_retry_after_header=False
        )
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=app.config["SPOTIFY_CLIENT_ID"],
            client_secret=app.config["SPOTIFY_CLIENT_SECRET"]
        ))

        init_cache(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'],
                   namespace=app.config['REDIS_NAMESPACE'])
        metrics.init("listenbrainz")

    def add_spotify_ids(self, album_id, priority=INCOMING_ALBUM_PRIORITY):
        spotify_id = album_id.split("/")[-1]
        self.queue.put(JobItem(priority, spotify_id))

    def terminate(self):
        self.done = True
        self.join()

    def update_metrics(self, stats):
        """ Calculate stats and print status to stdout and report metrics."""
        pending_count = self.queue.size()
        metrics.set("listenbrainz-spotify-metadata-cache", pending_count=pending_count)
        self.app.logger.info("Pending IDs in Queue: %d", pending_count)

    def fetch_album(self, album_id):
        album = self.sp.album(album_id)

        results = self.sp.album_tracks(album_id, limit=50)
        tracks = results.get("items")
        if not tracks:
            return album

        while results.get("next"):
            results = self.sp.next(results)
            if results.get("items"):
                tracks.extend(results.get("items"))

            for track in tracks:
                for track_artist in track.get("artists"):
                    if track_artist["id"]:
                        self.discover_albums(track_artist["id"])

            album["tracks"] = tracks

        return album

    def discover_albums(self, artist_id):
        if artist_id in self.discovered_artists:
            return
        self.discovered_artists.add(artist_id)

        results = self.sp.artist_albums(artist_id, album_type='album,single,compilation')
        albums = results.get('items')
        while results.get('next'):
            results = self.sp.next(results)
            if results.get('items'):
                albums.extend(results.get('items'))

        for album in albums:
            self.queue.put(JobItem(DISCOVERED_ALBUM_PRIORITY, album["id"]))

    def insert_album(self, spotify_id, data):
        last_refresh = datetime.utcnow()
        expires_at = datetime.utcnow() + timedelta(days=CACHE_TIME)
        with timescale.engine.begin() as ts_conn:
            query = """
                INSERT INTO mapping.spotify_metadata_cache (album_id, data, last_refresh, expires_at)
                     VALUES (:album_id, :data, :last_refresh, :expires_at)
                ON CONFLICT (album_id)
                  DO UPDATE SET
                            data = EXCLUDED.data
                          , last_refresh = EXCLUDED.last_refresh
                          , expires_at = EXCLUDED.expires_at
            """
            ts_conn.execute(text(query), {
                "spotify_id": spotify_id,
                "data": ujson.dumps(data),
                "last_refresh": last_refresh,
                "expires_at": expires_at
            })
        
        cache_key = CACHE_KEY_PREFIX + spotify_id
        cache.set(cache_key, 1, expirein=0)
        cache.expireat(cache_key, int(expires_at.timestamp()))

    def process_spotify_id(self, spotify_id):
        cache_key = CACHE_KEY_PREFIX + spotify_id
        if cache.get(cache_key) is not None:
            return

        # TODO: check in PG too if missing from cache before querying spotify?

        album_data = self.fetch_album(spotify_id)
        self.insert_album(spotify_id, album_data)

    def run(self):
        """ main thread entry point"""
        stats = {}

        # the main thread loop
        update_time = monotonic() + UPDATE_INTERVAL
        with self.app.app_context():
            while not self.done:
                try:
                    item = self.queue.get()
                    self.process_spotify_id(item.spotify_id)

                    if monotonic() > update_time:
                        update_time = monotonic() + UPDATE_INTERVAL
                        self.update_metrics(stats)
                except Empty:
                    sleep(5)
                except Exception:
                    self.app.logger.info(traceback.format_exc())

            self.app.logger.info("job queue thread finished")
