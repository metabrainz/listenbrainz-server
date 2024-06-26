from datetime import datetime, timedelta

import orjson
import urllib3
from brainzutils import cache
from psycopg2.extras import execute_values
from psycopg2.sql import SQL
from requests import Session
from requests.adapters import HTTPAdapter

from listenbrainz.db import timescale
from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.metadata_cache.soundcloud.models import SoundcloudTrack, SoundcloudArtist
from listenbrainz.metadata_cache.unique_queue import JobItem

DISCOVERED_USER_PRIORITY = 3
INCOMING_TRACK_PRIORITY = 0

PARTNER_API_URL = "https://api-partners.soundcloud.com"
TRACK_CACHE_TIME = 30 # days
USER_CACHE_TIME = 30 # days

SOUNDCLOUD_TRACK_PREFIX = "soundcloud:tracks:"
SOUNDCLOUD_USER_PREFIX = "soundcloud:users:"


class SoundcloudCrawlerHandler(BaseHandler):

    def __init__(self, app):
        super().__init__(
            name="listenbrainz-soundcloud-metadata-cache",
            external_service_queue=app.config["EXTERNAL_SERVICES_SOUNDCLOUD_CACHE_QUEUE"]
        )
        self.app = app

        self.discovered_artists = set()
        self.discovered_tracks = set()

        self.retry = urllib3.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            respect_retry_after_header=False
        )
        self.session = Session()
        self.session.headers.update({"Accept": "application/json; charset=utf-8"})
        self.adapter = HTTPAdapter(max_retries=self.retry)
        self.session.mount("http://", self.adapter)
        self.session.mount("https://", self.adapter)

    def make_request(self, endpoint, **kwargs):
        """ Make an API request to a soundcloud partner api endpoint"""
        response = self.session.get(
            PARTNER_API_URL + endpoint,
            params={**kwargs, "client_id": self.app.config["SOUNDCLOUD_CLIENT_ID"]}
        )
        response.raise_for_status()
        return response.json()

    def make_paginated_request(self, endpoint, **kwargs):
        """ Make an API request to a soundcloud partner api endpoint that supports pagination and retrieve all
         items in the collection.
        """
        tracks = []
        data = self.make_request(endpoint, limit=100, **kwargs)
        tracks.extend(data["collection"])

        while True:
            if len(data["collection"]) > 0 and "next_href" in data:
                url = data["next_href"]
                response = self.session.get(url)
                response.raise_for_status()
                data = response.json()
                tracks.extend(data["collection"])
            else:
                break

        return tracks

    def get_items_from_listen(self, listen) -> list[JobItem]:
        track_id = listen["track_metadata"]["additional_info"].get("soundcloud_track_id")
        if track_id:
            return [JobItem(INCOMING_TRACK_PRIORITY, track_id)]
        return []

    def get_items_from_seeder(self, message) -> list[JobItem]:
        return [JobItem(INCOMING_TRACK_PRIORITY, track_id) for track_id in message["soundcloud_track_ids"]]

    @staticmethod
    def transform_track(track) -> SoundcloudTrack:
        user = track.pop("user")
        artist = SoundcloudArtist(
            id=str(user["id"]),
            name=user["username"],
            data=user
        )
        return SoundcloudTrack(
            id=str(track["id"]),
            name=track["title"],
            artist=artist,
            data=track
        )

    def fetch_track_from_track_urn(self, track_urn: str) -> SoundcloudTrack:
        """ retrieve track data from soundcloud to store in the soundcloud metadata cache """
        data = self.make_request("/tracks/" + track_urn)
        track = self.transform_track(data)
        return track

    def fetch_tracks_from_user_urn(self, user_urn: str) -> list[SoundcloudTrack]:
        """ lookup tracks uploaded by the given user """
        if user_urn not in self.discovered_artists:
            self.discovered_artists.add(user_urn)
            self.metrics["discovered_artists_count"] += 1

        user_uploads = self.make_paginated_request("/users/" + user_urn + "/tracks/uploads")
        tracks = []
        for item in user_uploads:
            track = self.transform_track(item)
            if track.data["urn"] not in self.discovered_tracks:
                self.discovered_tracks.add(track.data["urn"])
                self.metrics["discovered_tracks_count"] += 1
            tracks.append(track)

        return tracks

    def discover_users_from_user_urn(self, user_urn: str) -> set[str]:
        """ search for new users to crawl in the given user's liked tracks and followings """
        new_user_urns = set()
        user_likes = self.make_paginated_request("/users/" + user_urn + "/likes/tracks")
        for track in user_likes:
            new_user_urns.add(track["user"]["urn"])
        followings = self.make_paginated_request("/users/" + user_urn + "/followings")
        for user in followings:
            new_user_urns.add(user["urn"])
        return new_user_urns


    def get_seed_ids(self) -> list[str]:
        """ Retrieve soundcloud track ids from new releases for all markets"""
        data = self.make_request("/trending")
        genres = data["categories"]["music"]

        track_urns = set()
        for genre in genres:
            response = self.make_request("/trending/music", anonymous_id=self.name, genres=genre, limit=100)
            for track in response["collection"]:
                track_urns.add(track["urn"])

        return list(track_urns)

    @staticmethod
    def insert(curs, tracks: list[SoundcloudTrack]):
        """ insert a list of soundcloud tracks in the database """
        query = SQL("""
            INSERT INTO soundcloud_cache.artist (artist_id, name, data)
                 VALUES %s
            ON CONFLICT (artist_id)
              DO UPDATE
                    SET name = EXCLUDED.name
                      , data = EXCLUDED.data
        """)
        artist_ids = set()
        values = []
        for track in tracks:
            artist = track.artist
            if artist.id not in artist_ids:
                values.append((artist.id, artist.name, orjson.dumps(artist.data).decode("utf-8")))
                artist_ids.add(artist.id)
        execute_values(curs, query, values)

        query = SQL("""
            INSERT INTO soundcloud_cache.track (track_id, name, artist_id, data)
                 VALUES %s
            ON CONFLICT (track_id)
              DO UPDATE
                    SET name = EXCLUDED.name
                      , artist_id = EXCLUDED.artist_id
                      , data = EXCLUDED.data
        """)
        values = [(t.id, t.name, t.artist.id, orjson.dumps(t.data).decode("utf-8")) for t in tracks]
        execute_values(curs, query, values)

    def update_cache(self, tracks: list[SoundcloudTrack]):
        """ Insert multiple tracks from in database and update their status in redis cache. """
        track_expires_at = datetime.now() + timedelta(days=TRACK_CACHE_TIME)
        track_expires_at_ts = int(track_expires_at.timestamp())

        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                self.insert(curs, tracks)
                for track in tracks:
                    cache.set(track.data["urn"], 1, expirein=0)
                    cache.expireat(track.data["urn"], track_expires_at_ts)
                    self.metrics["tracks_inserted_count"] += 1
                conn.commit()
        finally:
            conn.close()

    def process_track(self, track_urn) -> set[str]:
        """ Process a track_urn received from the crawler """
        if cache.get(track_urn):
            return set()
        track = self.fetch_track_from_track_urn(track_urn)
        self.update_cache([track])
        return {track.artist.data["urn"]}

    def process_user(self, user_urn) -> set[str]:
        """ Process a user_urn received from the crawler """
        if cache.get(user_urn):
            return set()
        user_tracks = self.fetch_tracks_from_user_urn(user_urn)
        if user_tracks:
            self.update_cache(user_tracks)

        artist_expires_at = datetime.now() + timedelta(days=USER_CACHE_TIME)
        artist_expires_at_ts = int(artist_expires_at.timestamp())
        cache.set(user_urn, 1, expirein=0)
        cache.expireat(user_urn, artist_expires_at_ts)

        return self.discover_users_from_user_urn(user_urn)

    def process(self, item_ids: list[str]) -> list[JobItem]:
        """ Processes the list of items (example: track ids) received from the crawler. """
        all_items = set()
        for item_id in item_ids:
            if item_id.startswith(SOUNDCLOUD_TRACK_PREFIX):
                items = self.process_track(item_id)
            elif item_id.startswith(SOUNDCLOUD_USER_PREFIX):
                items = self.process_user(item_id)
            else:
                items = set()
                self.app.logger.info("Invalid soundcloud urn: %s, skipping.", item_id)
            all_items |= items

        items = []
        for item in all_items:
            items.append(JobItem(DISCOVERED_USER_PRIORITY, item))
        return items
