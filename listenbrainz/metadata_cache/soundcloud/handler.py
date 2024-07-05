from datetime import datetime, timedelta

import orjson
import urllib3
from brainzutils import cache
from psycopg2.extras import execute_values
from psycopg2.sql import SQL
from requests import Session
from requests.adapters import HTTPAdapter

from listenbrainz.db import timescale
from listenbrainz.domain.soundcloud import SoundCloudService
from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.metadata_cache.soundcloud.models import SoundcloudTrack, SoundcloudArtist
from listenbrainz.metadata_cache.unique_queue import JobItem

DISCOVERED_USER_PRIORITY = 3
INCOMING_TRACK_PRIORITY = 0

PARTNER_API_URL = "https://api-partners.soundcloud.com"
PUBLIC_API_URL = "https://api.soundcloud.com"
TRACK_CACHE_TIME = 30 # days
USER_CACHE_TIME = 30 # days

SOUNDCLOUD_TRACK_PREFIX = "soundcloud:tracks:"
SOUNDCLOUD_USER_PREFIX = "soundcloud:users:"

# LB user authenticated to soundcloud whose soundcloud auth tokens should be used
# by the metadata cache to access the public API. One time manual linking to SoundCloud
# using ListenBrainz website needs to be performed for this user before it can be used
# by the cache.
LISTENBRAINZ_PROD_USER_ID = 15753


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
        self.soundcloud_service = SoundCloudService()
        self.access_token = None

    def refresh_access_token(self):
        soundcloud_user = self.soundcloud_service.get_user(LISTENBRAINZ_PROD_USER_ID)
        token = self.soundcloud_service.refresh_access_token(LISTENBRAINZ_PROD_USER_ID, soundcloud_user["refresh_token"])
        self.access_token = token["access_token"]

    def make_request(self, url, params=None, headers=None, retry=True):
        """ Make an authenticated request to SoundCloud API by adding the OAuth2 token to headers """
        if self.access_token is None:
            self.refresh_access_token()

        if headers is None:
            headers = {}
        headers["Authorization"] = f"OAuth {self.access_token}"

        response = self.session.get(url, params=params, headers=headers)
        if response.status_code == 401 and retry:
            self.refresh_access_token()
            return self.make_request(url, params, headers, retry=False)
        response.raise_for_status()
        return response.json()

    def make_partner_request(self, endpoint, **kwargs):
        """ Make an API request to a soundcloud partner api endpoint """
        url = PARTNER_API_URL + endpoint
        kwargs["client_id"] = self.app.config["SOUNDCLOUD_CLIENT_ID"]
        return self.make_request(url, params=kwargs)

    def make_public_request(self, endpoint, **kwargs):
        """ Make an API request to a soundcloud public api endpoint """
        url = PUBLIC_API_URL + endpoint
        return self.make_request(url, params=kwargs)

    def make_public_paginated_request(self, endpoint, **kwargs):
        """ Make an API request to a soundcloud public api endpoint that supports pagination and retrieve all
         items in the collection.
        """
        tracks = []
        data = self.make_public_request(endpoint, limit=100, linked_partitioning=True, **kwargs)
        tracks.extend(data["collection"])

        while True:
            if len(data["collection"]) > 0 and "next_href" in data and data["next_href"]:
                url = data["next_href"]
                data = self.make_request(url)
                tracks.extend(data["collection"])
            else:
                break

        return tracks

    def get_items_from_listen(self, listen) -> list[JobItem]:
        """ Extract soundcloud ids from incoming listen """
        track_id = listen["track_metadata"]["additional_info"].get("soundcloud_track_id")
        if track_id:
            return [JobItem(INCOMING_TRACK_PRIORITY, track_id)]
        return []

    def get_items_from_seeder(self, message) -> list[JobItem]:
        """ Extract soundcloud ids from messages enqueued by seeder """
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
            release_year=track.get("release_year"),
            release_month=track.get("release_month"),
            release_day=track.get("release_day"),
            artist=artist,
            data=track
        )

    def fetch_track_from_track_id(self, track_id: int) -> SoundcloudTrack:
        """ retrieve track data from soundcloud to store in the soundcloud metadata cache """
        data = self.make_public_request(f"/tracks/{track_id}")
        track = self.transform_track(data)
        return track

    def fetch_tracks_from_user_id(self, user_id: int) -> list[SoundcloudTrack]:
        """ lookup tracks uploaded by the given user """
        if user_id not in self.discovered_artists:
            self.discovered_artists.add(user_id)
            self.metrics["discovered_artists_count"] += 1

        user_uploads = self.make_public_paginated_request(f"/users/{user_id}/tracks")
        tracks = []
        for item in user_uploads:
            track = self.transform_track(item)
            if track.data["id"] not in self.discovered_tracks:
                self.discovered_tracks.add(track.data["id"])
                self.metrics["discovered_tracks_count"] += 1
            tracks.append(track)

        return tracks

    def discover_users_from_user_id(self, user_id: int) -> set[str]:
        """ search for new users to crawl in the given user's liked tracks and followings """
        new_user_ids = set()
        user_likes = self.make_public_paginated_request(f"/users/{user_id}/likes/tracks")
        for track in user_likes:
            new_user_ids.add(track["user"]["id"])
        followings = self.make_public_paginated_request(f"/users/{user_id}/followings")
        for user in followings:
            new_user_ids.add(user["id"])
        followers = self.make_public_paginated_request(f"/users/{user_id}/followers")
        for user in followers:
            new_user_ids.add(user["id"])
        new_user_urns = {SOUNDCLOUD_USER_PREFIX + str(user_id) for user_id in new_user_ids}
        return new_user_urns

    def get_seed_ids(self) -> list[str]:
        """ Retrieve soundcloud track ids from new releases for all markets"""
        data = self.make_partner_request("/trending")
        genres = data["categories"]["music"]

        track_urns = set()
        for genre in genres:
            response = self.make_partner_request("/trending/music", anonymous_id=self.name, genres=genre, limit=100)
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
            INSERT INTO soundcloud_cache.track (track_id, name, artist_id, release_year, release_month, release_day, data)
                 VALUES %s
            ON CONFLICT (track_id)
              DO UPDATE
                    SET name = EXCLUDED.name
                      , artist_id = EXCLUDED.artist_id
                      , data = EXCLUDED.data
        """)
        values = [(t.id, t.name, t.artist.id, t.release_year, t.release_month, t.release_day, orjson.dumps(t.data).decode("utf-8")) for t in tracks]
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
                    track_urn = SOUNDCLOUD_TRACK_PREFIX + str(track.data["id"])
                    cache.set(track_urn, 1, expirein=0)
                    cache.expireat(track_urn, track_expires_at_ts)
                    self.metrics["tracks_inserted_count"] += 1
                conn.commit()
        finally:
            conn.close()

    def process_track(self, track_urn) -> set[str]:
        """ Process a track_urn received from the crawler """
        if cache.get(track_urn):
            return set()
        track_id = int(track_urn.split(":")[-1])
        track = self.fetch_track_from_track_id(track_id)
        self.update_cache([track])
        return {SOUNDCLOUD_USER_PREFIX + str(track.artist.data["id"])}

    def process_user(self, user_urn) -> set[str]:
        """ Process a user_urn received from the crawler """
        if cache.get(user_urn):
            return set()
        user_id = int(user_urn.split(":")[-1])
        user_tracks = self.fetch_tracks_from_user_id(user_id)
        if user_tracks:
            self.update_cache(user_tracks)

        artist_expires_at = datetime.now() + timedelta(days=USER_CACHE_TIME)
        artist_expires_at_ts = int(artist_expires_at.timestamp())
        cache.set(user_urn, 1, expirein=0)
        cache.expireat(user_urn, artist_expires_at_ts)

        return self.discover_users_from_user_id(user_id)

    def process(self, item_ids: list[str]) -> list[JobItem]:
        """ Processes the list of items (example: track ids) received from the crawler. """
        all_items = set()
        for item_urn in item_ids:
            if item_urn.startswith(SOUNDCLOUD_TRACK_PREFIX):
                items = self.process_track(item_urn)
            elif item_urn.startswith(SOUNDCLOUD_USER_PREFIX):
                items = self.process_user(item_urn)
            else:
                items = set()
                self.app.logger.error("Invalid soundcloud urn: %s, skipping.", item_urn)
            all_items |= items

        items = []
        for item in all_items:
            items.append(JobItem(DISCOVERED_USER_PRIORITY, item))
        return items
