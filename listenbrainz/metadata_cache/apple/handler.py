import traceback

import sentry_sdk

from listenbrainz.metadata_cache.album_handler import AlbumHandler
from listenbrainz.metadata_cache.apple.client import Apple
from listenbrainz.metadata_cache.models import Album, Artist, Track, AlbumType
from listenbrainz.metadata_cache.unique_queue import JobItem

UPDATE_INTERVAL = 60  # in seconds
CACHE_TIME = 180  # in days
BATCH_SIZE = 10  # number of apple ids to process at a time

DISCOVERED_ALBUM_PRIORITY = 3
INCOMING_ALBUM_PRIORITY = 0

CACHE_KEY_PREFIX = "apple:album:"


class AppleCrawlerHandler(AlbumHandler):

    def __init__(self, app):
        super().__init__(
            name="listenbrainz-apple-metadata-cache",
            external_service_queue=app.config["EXTERNAL_SERVICES_APPLE_CACHE_QUEUE"],
            schema_name="apple_cache",
            cache_key_prefix=CACHE_KEY_PREFIX
        )
        self.app = app
        self.discovered_albums = set()
        self.discovered_artists = set()
        self.client = Apple()

    def get_seed_ids(self) -> list[str]:
        """ Retrieve apple album ids from new releases for all markets"""
        client = Apple()
        storefronts = client.get("https://api.music.apple.com/v1/storefronts")
        album_ids = set()
        for storefront in storefronts["data"]:
            storefront_code = storefront["id"]
            response = client.get(f"https://api.music.apple.com/v1/catalog/{storefront_code}/charts", {
                "types": "albums",
                "limit": 200
            })
            album_ids |= {album["id"] for album in response["results"]["albums"][0]["data"]}
        return list(album_ids)

    def get_items_from_listen(self, listen) -> list[JobItem]:
        """ convert listens to job itees to be enqueued in crawler """
        album_id = listen["track_metadata"]["additional_info"].get("apple_album_id")
        if album_id:
            return [JobItem(INCOMING_ALBUM_PRIORITY, album_id)]
        return []

    def get_items_from_seeder(self, message) -> list[JobItem]:
        """ convert album_ids from seeder to job items to be enqueued in crawler """
        return [JobItem(INCOMING_ALBUM_PRIORITY, album_id) for album_id in message["apple_album_ids"]]

    @staticmethod
    def transform_album(album) -> Album:
        """ convert an album response from apple API to Album object for storing in db """
        tracks = []
        for track in album.pop("tracks"):
            track_artists = []
            if "relationships" in track:
                for artist in track.pop("relationships")["artists"]["data"]:
                    artist.pop("relationships")
                    track_artists.append(Artist(id=artist["id"], name=artist["attributes"]["name"], data=artist))

            tracks.append(Track(
                id=track["id"],
                name=track["attributes"]["name"],
                track_number=track["attributes"]["trackNumber"],
                artists=track_artists,
                data=track
            ))

        artists = []
        for artist in album.pop("artists"):
            artist.pop("relationships", None)
            artists.append(Artist(id=artist["id"], name=artist["attributes"]["name"], data=artist))

        if album["attributes"]["isSingle"]:
            album_type = AlbumType.single
        elif album["attributes"]["isCompilation"]:
            album_type = AlbumType.compilation
        else:
            album_type = AlbumType.album

        return Album(
            id=album["id"],
            name=album["attributes"]["name"],
            type_=album_type,
            release_date=album["attributes"]["releaseDate"],
            tracks=tracks,
            artists=artists,
            data=album
        )

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

        transformed_albums = [self.transform_album(album) for album in albums]
        return transformed_albums, new_items

    def discover_albums(self, artist_id) -> list[JobItem]:
        """ lookup albums of the given artist to discover more albums to seed the job queue """
        new_items = []
        try:
            if artist_id in self.discovered_artists:
                return []
            self.discovered_artists.add(artist_id)
            self.metrics["discovered_artists_count"] += 1

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

            for album_id in album_ids:
                self.discovered_albums.add(album_id)
                self.metrics["discovered_albums_count"] += 1
                new_items.append(JobItem(DISCOVERED_ALBUM_PRIORITY, album_id))
        except Exception as e:
            sentry_sdk.capture_exception(e)
            self.app.logger.info(traceback.format_exc())
        return new_items
