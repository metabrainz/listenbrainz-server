import abc
from datetime import datetime, timedelta

from brainzutils import cache

from listenbrainz.db import timescale
from listenbrainz.mbid_mapping_writer.job_queue import JobItem
from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.metadata_cache.models import Album
from listenbrainz.metadata_cache.store import insert

CACHE_TIME = 180  # in days


class AlbumHandler(BaseHandler):

    def __init__(self, name, external_service_queue, schema_name, cache_key_prefix):
        """
            A base class that abstracts common functionality for working with metadata service crawler
            for external services that have albums as an easy discovery point.

            Args:
                name: the name of crawler service
                external_service_queue: the name of the queue to which the associated seeder writes to
                schema_name: the name of the schema in which the associated metadata cache tables are stored
                cache_key_prefix: the prefix added to service identifiers when generating the cache keys
        """
        super().__init__(name, external_service_queue)
        self.schema_name = schema_name
        self.cache_key_prefix = cache_key_prefix

    def get_cache_key(self, item_id: str) -> str:
        """ Get the cache key for the given item_id """
        return self.cache_key_prefix + item_id

    @abc.abstractmethod
    def get_items_from_listen(self, listen) -> list[JobItem]:
        """ Convert a listen to job items to be enqueued to the crawler. """
        pass

    @abc.abstractmethod
    def get_items_from_seeder(self, message) -> list[JobItem]:
        """ Convert a message from the seeder to job items to be enqueued to the crawler. """
        pass

    @abc.abstractmethod
    def fetch_albums(self, album_ids: list[str]) -> tuple[list[Album], list[JobItem]]:
        """ For the given album_ids, return a tuple of the metadata retrieved from external service
         and a list of newly discovered items.
        """
        pass

    def check_and_fetch_albums(self, album_ids) -> tuple[list[Album], list[JobItem]]:
        """ Checks if the albums are present in the cache and not expired yet before querying external services """
        filtered_ids = []
        for album_id in album_ids:
            cache_key = self.get_cache_key(album_id)
            if cache.get(cache_key) is None:
                filtered_ids.append(album_id)
        if not filtered_ids:
            return [], []

        albums, new_items = self.fetch_albums(filtered_ids)
        filtered_albums = [x for x in albums if x is not None]
        return filtered_albums, new_items

    def update_cache(self, albums: list[Album]):
        """ Insert multiple albums in database and update their status in redis cache. """
        last_refresh = datetime.now()
        expires_at = datetime.now() + timedelta(days=CACHE_TIME)

        conn = timescale.engine.raw_connection()
        try:
            with conn.cursor() as curs:
                for album in albums:
                    insert(curs, self.schema_name, album, last_refresh, expires_at)

                    cache_key = self.get_cache_key(album.id)
                    cache.set(cache_key, 1, expirein=0)
                    cache.expireat(cache_key, int(expires_at.timestamp()))

                    self.metrics["albums_inserted"] += 1
                    conn.commit()
        finally:
            conn.close()

    def process(self, album_ids: list[str]) -> list[JobItem]:
        """ Processes the list of items (example: album ids) received from the crawler.

            During processing new items maybe found for processing, for example discovering a new artist
            and then their albums.

            Returns a list of job items to be enqueued to the crawler for processing in the future.
        """
        albums, new_items = self.check_and_fetch_albums(album_ids)
        if albums:
            self.update_cache(albums)
        return new_items
