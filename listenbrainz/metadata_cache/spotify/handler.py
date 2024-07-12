import traceback

import sentry_sdk
import spotipy
import urllib3
from spotipy import SpotifyClientCredentials

from listenbrainz.metadata_cache.album_handler import AlbumHandler
from listenbrainz.metadata_cache.models import Album, Artist, Track
from listenbrainz.metadata_cache.unique_queue import JobItem

DISCOVERED_ALBUM_PRIORITY = 3
INCOMING_ALBUM_PRIORITY = 0
CACHE_KEY_PREFIX = "spotify:album:"


class SpotifyCrawlerHandler(AlbumHandler):

    def __init__(self, app):
        super().__init__(
            name="listenbrainz-spotify-metadata-cache",
            external_service_queue=app.config["EXTERNAL_SERVICES_SPOTIFY_CACHE_QUEUE"],
            schema_name="spotify_cache",
            cache_key_prefix=CACHE_KEY_PREFIX
        )
        self.app = app
        self.discovered_albums = set()
        self.discovered_artists = set()

        self.retry = urllib3.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            respect_retry_after_header=False
        )
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=app.config["SPOTIFY_CACHE_CLIENT_ID"],
            client_secret=app.config["SPOTIFY_CACHE_CLIENT_SECRET"]
        ))

    def get_items_from_listen(self, listen) -> list[JobItem]:
        album_id = listen["track_metadata"]["additional_info"].get("spotify_album_id")
        if album_id:
            return [JobItem(INCOMING_ALBUM_PRIORITY, album_id)]
        return []

    def get_items_from_seeder(self, message) -> list[JobItem]:
        return [JobItem(INCOMING_ALBUM_PRIORITY, album_id) for album_id in message["spotify_album_ids"]]

    @staticmethod
    def transform_album(album) -> Album:
        tracks = []
        for track in album.pop("tracks"):
            track_artists = [
                Artist(id=artist["id"], name=artist["name"], data=artist)
                for artist in track.pop("artists")
            ]
            tracks.append(Track(
                id=track["id"],
                name=track["name"],
                track_number=track["track_number"],
                artists=track_artists,
                data=track
            ))

        artists = []
        for artist in album.pop("artists"):
            artists.append(Artist(id=artist["id"], name=artist["name"], data=artist))

        return Album(
            id=album["id"],
            name=album["name"],
            type_=album["album_type"],
            release_date=album["release_date"],
            tracks=tracks,
            artists=artists,
            data=album
        )

    def fetch_albums(self, album_ids) -> tuple[list[Album], list[JobItem]]:
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

        transformed_albums = [self.transform_album(album) for album in albums]

        return transformed_albums, new_items

    def discover_albums(self, artist_id) -> list[JobItem]:
        """ lookup albums of the given artist to discover more albums to seed the job queue """
        new_items = []
        try:
            if artist_id in self.discovered_artists:
                return new_items
            self.discovered_artists.add(artist_id)
            self.metrics["discovered_artists_count"] += 1

            results = self.sp.artist_albums(artist_id, album_type='album,single,compilation', limit=50)
            albums = results.get('items')
            while results.get('next'):
                results = self.sp.next(results)
                if results.get('items'):
                    albums.extend(results.get('items'))

            for album in albums:
                if album["id"] not in self.discovered_albums:
                    self.discovered_albums.add(album["id"])
                    self.metrics["discovered_albums_count"] += 1
                    new_items.append(JobItem(DISCOVERED_ALBUM_PRIORITY, album["id"]))

        except Exception as e:
            sentry_sdk.capture_exception(e)
            self.app.logger.info(traceback.format_exc())

        return new_items

    def get_seed_ids(self) -> list[str]:
        """ Retrieve spotify album ids from new releases for all markets"""
        markets = self.sp.available_markets()["markets"]

        album_ids = set()
        for market in markets:
            result = self.sp.new_releases(market, limit=50)
            album_ids |= {album["id"] for album in result["albums"]["items"]}

            while result.get("next"):
                result = self.sp.next(result)
                album_ids |= {album["id"] for album in result["albums"]["items"]}

        return list(album_ids)
