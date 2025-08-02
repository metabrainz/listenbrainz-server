import logging
import json
from sqlalchemy import text
import internetarchive
from bs4 import BeautifulSoup
from brainzutils import cache
from listenbrainz.db import timescale
from listenbrainz.metadata_cache.handler import BaseHandler
from listenbrainz.metadata_cache.unique_queue import JobItem

logger = logging.getLogger(__name__)

AUDIO_KEYWORDS = [
    "mp3", "ogg", "vorbis", "flac", "wav", "aiff", "apple lossless", "m4a", "opus", "aac",
    "au", "wma", "alac", "ape", "shn", "tta", "wv", "mpc", "aifc", "m4b", "m4p", "vbr", 
    "m3u", "cylinder", "78rpm", "lossless", "lossy", "webm", "aif", "mid", "midi", "amr",
    "ra", "rm", "vox", "dts", "ac3", "atrac", "pcm", "adpcm", "gsm", "mmf", "3ga", "8svx"
]


class InternetArchiveHandler(BaseHandler):
    def __init__(self, app):
        super().__init__(
            name="listenbrainz-internetarchive-metadata-cache",
            external_service_queue=app.config.get("EXTERNAL_SERVICES_IA_CACHE_QUEUE", "ia_metadata_seed")
        )
        self.app = app
        self.database = timescale.engine
        self.redis = cache._r

    def get_items_from_listen(self, listen):
        return []

    def get_items_from_seeder(self, message):
        return [JobItem(0, identifier) for identifier in message.get("ia_identifiers", [])]

    def get_seed_ids(self, limit_per_collection=1000) -> list[str]:
        """Fetch identifiers for 78rpm and cylinder collections."""
        collections = [
            {'name': '78rpm', 'query': 'collection:78rpm AND mediatype:audio'},
            {'name': 'cylinder', 'query': 'cylinder mediatype:audio'}
        ]
        identifiers = []
        for collection in collections:
            results = internetarchive.search_items(collection['query'])
            count = 0
            for item in results:
                if count >= limit_per_collection:
                    break
                identifier = item.get('identifier')
                if identifier:
                    identifiers.append(identifier)
                    count += 1
        return identifiers

    def process(self, item_ids):
        """Process a list of IA identifiers."""
        for identifier in item_ids:
            redis_key = f"ia_metadata_cache:{identifier}"
            if self.redis.get(redis_key):
                logger.info("Skipping cached: %s", identifier)
                continue
            try:
                with self.database.begin() as conn:
                    self.process_identifier(identifier, conn)
                    self.redis.setex(redis_key, 86400, "1")
            except Exception as e:
                logger.error("Error processing %s: %s", identifier, str(e), exc_info=True)
        return []

    @staticmethod
    def extract_from_description(description, field):
        """
        Extracts a field (e.g. 'Artist', 'Album') from the IA description HTML using BeautifulSoup.
        Handles both string and list input.
        """
        if not description:
            return None
        if isinstance(description, list):
            description = " ".join(str(x) for x in description if x)

        try:
            soup = BeautifulSoup(description, "html.parser")
            for element in soup.find_all(['div', 'p', 'span']):
                _text = element.get_text(strip=True)
                if _text.startswith(f"{field}:"):
                    return _text[len(field) + 1:].strip()
        except Exception as e:
            logger.error("Error parsing description HTML: %s", str(e))
        return None

    def process_identifier(self, identifier, conn):
        try:
            item = internetarchive.get_item(identifier)
            item_metadata = item.item_metadata
            meta = item_metadata.get("metadata", {})
            files = item_metadata.get("files", [])
        except Exception as e:
            logger.error("Failed to fetch %s: %s", identifier, str(e))
            return

        stream_urls = []
        artwork_url = None

        for f in files:
            fmt = f.get("format", "").lower()
            if any(keyword in fmt for keyword in AUDIO_KEYWORDS):
                stream_urls.append(f"https://archive.org/download/{identifier}/{f['name']}")
            if not artwork_url and fmt in {"jpeg", "jpg", "png"}:
                artwork_url = f"https://archive.org/download/{identifier}/{f['name']}"

        artist = meta.get("creator")
        if not artist:
            artist = self.extract_from_description(meta.get("description", ""), "Artist")
        if isinstance(artist, str):
            artist = [artist]
        elif artist is None:
            artist = []

        album = meta.get("album")
        if not album:
            album = self.extract_from_description(meta.get("description", ""), "Album")

        conn.execute(
            text("""
                INSERT INTO internetarchive_cache.track
                    (track_id, name, artist, album, stream_urls, artwork_url, data, last_updated)
                VALUES
                    (:track_id, :name, :artist, :album, :stream_urls, :artwork_url, :data, NOW())
                ON CONFLICT (track_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    artist = EXCLUDED.artist,
                    album = EXCLUDED.album,
                    stream_urls = EXCLUDED.stream_urls,
                    artwork_url = EXCLUDED.artwork_url,
                    data = EXCLUDED.data,
                    last_updated = NOW()
            """),
            {
                "track_id": f"https://archive.org/details/{identifier}",
                "name": meta.get("title", ""),
                "artist": artist,
                "album": album,
                "stream_urls": stream_urls,
                "artwork_url": artwork_url,
                "data": json.dumps(meta),
            }
        )
        logger.info("Processed and stored metadata for %s", identifier)
