import traceback
from collections import Counter
from datetime import datetime, timedelta

import sentry_sdk

from listenbrainz.db import timescale
from listenbrainz.metadata_cache.apple.client import Apple
from listenbrainz.metadata_cache.apple.store import insert

from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.metadata_cache.unique_queue import JobItem
from brainzutils import cache

UPDATE_INTERVAL = 60  # in seconds
CACHE_TIME = 180  # in days
BATCH_SIZE = 10  # number of apple ids to process at a time

DISCOVERED_ALBUM_PRIORITY = 3
INCOMING_ALBUM_PRIORITY = 0

CACHE_KEY_PREFIX = "apple:album:"


class AppleCrawlerHandler(BaseHandler):

    def __init__(self, app):
        self.app = app
        self.discovered_albums = set()
        self.discovered_artists = set()
        self.stats = Counter()
        self.client = Apple()

    def get_name(self) -> str:
        return "listenbrainz-apple-metadata-cache"

    def get_external_service_queue_name(self) -> str:
        return self.app.config["EXTERNAL_SERVICES_SPOTIFY_CACHE_QUEUE"]

    def get_items_from_listen(self, listen) -> list[JobItem]:
        album_id = listen["track_metadata"]["additional_info"].get("apple_album_id")
        if album_id:
            return [JobItem(INCOMING_ALBUM_PRIORITY, album_id)]
        return []

    def get_items_from_seeder(self, message) -> list[JobItem]:
        return [JobItem(INCOMING_ALBUM_PRIORITY, album_id) for album_id in message["album_ids"]]

    def update_metrics(self) -> dict:
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

    def fetch_albums(self, album_ids):
        """ retrieve album data from apple to store in the apple metadata cache """
        response = self.client.get("https://api.music.apple.com/v1/catalog/us/albums", {
            "ids": album_ids,
            "include": "artists",
            "include[songs]": "artists",
        })
        albums = response["data"]

        new_items = []

        for album in albums:
            tracks = []

            relationships = album.pop("relationships")
            tracks.extend(relationships["tracks"]["data"])

            next_url = relationships["tracks"].get("next")
            while next_url:
                new_response = self.client.get("https://api.music.apple.com" + next_url)
                tracks.extend(new_response["data"])
                next_url = new_response.get("next")

            for artist in relationships["artists"]["data"]:
                new_items.extend(self.discover_albums(artist["id"]))

            album["tracks"] = tracks
            album["artists"] = relationships["artists"]["data"]

        return albums, new_items

    def discover_albums(self, artist_id) -> list[JobItem]:
        """ lookup albums of the given artist to discover more albums to seed the job queue """
        try:
            if artist_id in self.discovered_artists:
                return []
            self.discovered_artists.add(artist_id)

            album_ids = []
            while True:
                try:
                    response = self.client.get(
                        f"https://api.music.apple.com/v1/catalog/us/artists/{artist_id}/albums",
                        {"limit": 100, "offset": len(album_ids)}
                    )
                    album_ids.extend([album["id"] for album in response["data"]])
                except Exception:
                    break

            new_items = []
            for album_id in album_ids:
                self.discovered_albums.add(album_id)
                new_items.append(JobItem(DISCOVERED_ALBUM_PRIORITY, album_id))
            return new_items
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
                insert(curs, data, last_refresh, expires_at)
            conn.commit()
        finally:
            conn.close()

        cache_key = CACHE_KEY_PREFIX + data["id"]
        cache.set(cache_key, 1, expirein=0)
        cache.expireat(cache_key, int(expires_at.timestamp()))

        self.stats["albums_inserted"] += 1

    def process_items(self, apple_ids: list[str]) -> list[JobItem]:
        filtered_ids = []
        for apple_id in apple_ids:
            cache_key = CACHE_KEY_PREFIX + apple_id
            if cache.get(cache_key) is None:
                filtered_ids.append(apple_id)

        if len(filtered_ids) == 0:
            return []

        albums, new_items = self.fetch_albums(filtered_ids)
        for album in albums:
            if album is None:
                continue
            self.insert(album)
        return new_items
