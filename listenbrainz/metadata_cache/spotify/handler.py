import traceback
from collections import Counter
from datetime import datetime, timedelta

import sentry_sdk
import spotipy
import urllib3
from brainzutils import cache
from spotipy import SpotifyClientCredentials

from listenbrainz.db import timescale
from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.metadata_cache.spotify.store import insert_normalized, insert_raw
from listenbrainz.metadata_cache.unique_queue import JobItem

DISCOVERED_ALBUM_PRIORITY = 3
INCOMING_ALBUM_PRIORITY = 0
CACHE_KEY_PREFIX = "spotify:album:"
CACHE_TIME = 180  # in days


class SpotifyCrawlerHandler(BaseHandler):

    def __init__(self, app):
        self.app = app
        self.discovered_albums = set()
        self.discovered_artists = set()
        self.stats = Counter()

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

    def get_name(self) -> str:
        return "listenbrainz-spotify-metadata-cache"

    def get_external_service_queue_name(self) -> str:
        return self.app.config["EXTERNAL_SERVICES_SPOTIFY_CACHE_QUEUE"]

    def get_items_from_listen(self, listen) -> list[JobItem]:
        album_id = listen["track_metadata"]["additional_info"].get("spotify_album_id")
        if album_id:
            return [JobItem(INCOMING_ALBUM_PRIORITY, album_id)]
        return []

    def get_items_from_seeder(self, message) -> list[JobItem]:
        return [JobItem(INCOMING_ALBUM_PRIORITY, album_id) for album_id in message["album_ids"]]

    def update_metrics(self) -> dict:
        """ Calculate stats and print status to stdout and report metrics."""
        discovered_artists_count = len(self.discovered_artists)
        discovered_albums_count = len(self.discovered_albums)
        self.app.logger.info("Artists discovered so far: %d", discovered_artists_count)
        self.app.logger.info("Albums discovered so far: %d", discovered_albums_count)
        self.app.logger.info("Albums inserted so far: %d", self.stats["albums_inserted"])
        return {
            "discovered_artists_count": discovered_artists_count,
            "discovered_albums_count": discovered_albums_count,
            "albums_inserted": self.stats["albums_inserted"]
        }

    def fetch_albums(self, album_ids) -> tuple[list[dict], list[JobItem]]:
        """ retrieve album data from spotify to store in the spotify metadata cache """
        new_items = []
        albums = self.sp.albums(album_ids).get("albums")

        for album in albums:
            if album is None:
                continue

            results = album["tracks"]
            tracks = results.get("items")

            while results.get("next"):
                results = self.sp.next(results)
                if results.get("items"):
                    tracks.extend(results.get("items"))

            for track in tracks:
                for track_artist in track.get("artists"):
                    if track_artist["id"]:
                        discovered_items = self.discover_albums(track_artist["id"])
                        new_items.extend(discovered_items)

            album["tracks"] = tracks

        return albums, new_items

    def discover_albums(self, artist_id) -> list[JobItem]:
        """ lookup albums of the given artist to discover more albums to seed the job queue """
        new_items = []
        try:
            if artist_id in self.discovered_artists:
                return new_items
            self.discovered_artists.add(artist_id)

            results = self.sp.artist_albums(artist_id, album_type='album,single,compilation', limit=50)
            albums = results.get('items')
            while results.get('next'):
                results = self.sp.next(results)
                if results.get('items'):
                    albums.extend(results.get('items'))

            for album in albums:
                if album["id"] not in self.discovered_albums:
                    self.discovered_albums.add(album["id"])
                    new_items.append(JobItem(DISCOVERED_ALBUM_PRIORITY, album["id"]))

        except Exception as e:
            sentry_sdk.capture_exception(e)
            self.app.logger.info(traceback.format_exc())

        return new_items

    def insert(self, data):
        """ insert album data into the spotify metadata cache """
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

    def process_items(self, spotify_ids) -> list[JobItem]:
        filtered_ids = []
        for spotify_id in spotify_ids:
            cache_key = CACHE_KEY_PREFIX + spotify_id
            if cache.get(cache_key) is None:
                filtered_ids.append(spotify_id)

        if len(filtered_ids) == 0:
            return []

        # TODO: check in PG too if missing from cache before querying spotify?

        albums, new_items = self.fetch_albums(filtered_ids)
        for album in albums:
            if album is None:
                continue
            self.insert(album)
        return new_items
