import traceback
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from queue import Empty, PriorityQueue
from time import monotonic, sleep
import threading

import sentry_sdk

from listenbrainz.apple_metadata_cache.apple import Apple
from listenbrainz.db import timescale
from listenbrainz.apple_metadata_cache.store import insert_normalized, insert_raw
from listenbrainz.spotify_metadata_cache.spotify_lookup_queue import UniqueQueue, JobItem
from listenbrainz.utils import init_cache
from brainzutils import metrics, cache

UPDATE_INTERVAL = 60  # in seconds
CACHE_TIME = 180  # in days
BATCH_SIZE = 10  # number of apple ids to process at a time

DISCOVERED_ALBUM_PRIORITY = 3
INCOMING_ALBUM_PRIORITY = 0

CACHE_KEY_PREFIX = "apple:album:"


class AppleIdsQueue(threading.Thread):
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
        self.stats = Counter()

        self.client = Apple()

        init_cache(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'],
                   namespace=app.config['REDIS_NAMESPACE'])
        metrics.init("listenbrainz")

    def add_apple_ids(self, album_id, priority=INCOMING_ALBUM_PRIORITY):
        """ add given apple ids to the job queue """
        apple_id = album_id.split("/")[-1]
        self.queue.put(JobItem(priority, apple_id))

    def terminate(self):
        self.done = True
        self.join()

    def update_metrics(self):
        """ Calculate stats and print status to stdout and report metrics."""
        pending_count = self.queue.size()
        discovered_artists_count = len(self.discovered_artists)
        metrics.set(
            "listenbrainz-apple-metadata-cache",
            pending_count=pending_count,
            discovered_artists_count=discovered_artists_count,
            discovered_albums_count=self.stats["discovered_albums"],
            albums_inserted=self.stats["albums_inserted"]
        )
        self.app.logger.info("Pending IDs in Queue: %d", pending_count)
        self.app.logger.info("Artists discovered so far: %d", discovered_artists_count)
        self.app.logger.info("Albums discovered so far: %d", self.stats["discovered_albums"])
        self.app.logger.info("Albums inserted so far: %d", self.stats["albums_inserted"])

    def fetch_albums(self, album_ids):
        """ retrieve album data from apple to store in the apple metadata cache """
        response = self.client.get("https://api.music.apple.com/v1/catalog/us/albums", {"ids": album_ids})
        albums = response["data"]

        for album in albums:
            tracks = []
            tracks.extend(album["relationships"]["tracks"]["data"])

            next_url = album["relationships"]["tracks"].get("next")
            while next_url:
                new_response = self.client.get("https://api.music.apple.com" + next_url)
                tracks.extend(new_response["data"])
                next_url = new_response.get("next")

            album["tracks"] = tracks

        return albums

    def discover_albums(self, artist_id):
        """ lookup albums of the given artist to discover more albums to seed the job queue """
        try:
            if artist_id in self.discovered_artists:
                return
            self.discovered_artists.add(artist_id)

            results = self.client.artist_albums(artist_id, album_type='album,single,compilation', limit=50)
            albums = results.get('items')
            while results.get('next'):
                results = self.client.next(results)
                if results.get('items'):
                    albums.extend(results.get('items'))

            for album in albums:
                was_added = self.queue.put(JobItem(DISCOVERED_ALBUM_PRIORITY, album["id"]))
                if was_added:
                    self.stats["discovered_albums"] += 1
        except Exception as e:
            sentry_sdk.capture_exception(e)
            self.app.logger.info(traceback.format_exc())

    def insert(self, data):
        """ insert album data into the apple metadata cache """
        last_refresh = datetime.utcnow()
        expires_at = datetime.utcnow() + timedelta(days=CACHE_TIME)

        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                # do raw insert first because normalized insert modifies data inplace.
                # keeping raw inserts for now incase we want to alter the normalized schema.
                insert_raw(curs, data, last_refresh, expires_at)
                insert_normalized(curs, data, last_refresh, expires_at)
            conn.commit()
        finally:
            conn.close()

        cache_key = CACHE_KEY_PREFIX + data["id"]
        cache.set(cache_key, 1, expirein=0)
        cache.expireat(cache_key, int(expires_at.timestamp()))

        self.stats["albums_inserted"] += 1

    def process_apple_ids(self, apple_ids):
        filtered_ids = []
        for apple_id in apple_ids:
            cache_key = CACHE_KEY_PREFIX + apple_id
            if cache.get(cache_key) is None:
                filtered_ids.append(apple_id)

        if len(filtered_ids) == 0:
            return

        # TODO: check in PG too if missing from cache before querying apple?

        albums = self.fetch_albums(filtered_ids)
        for album in albums:
            if album is None:
                continue
            self.insert(album)

    def run(self):
        """ main thread entry point"""
        # the main thread loop
        update_time = monotonic() + UPDATE_INTERVAL
        with self.app.app_context():
            while not self.done:
                if monotonic() > update_time:
                    update_time = monotonic() + UPDATE_INTERVAL
                    self.update_metrics()

                apple_ids = []

                try:
                    for _ in range(BATCH_SIZE):
                        item = self.queue.get()
                        apple_ids.append(item.apple_id)
                except Empty:
                    if len(apple_ids) == 0:
                        sleep(5)
                        continue

                try:
                    self.process_apple_ids(apple_ids)
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    self.app.logger.info(traceback.format_exc())

            self.app.logger.info("job queue thread finished")
