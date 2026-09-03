import logging
import json
from datetime import datetime, timedelta
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

DISCOVERED_ITEM_PRIORITY = 3
INCOMING_ITEM_PRIORITY = 0


class InternetArchiveHandler(BaseHandler):
    def __init__(self, app):
        super().__init__(
            name="listenbrainz-internetarchive-metadata-cache",
            external_service_queue=app.config["EXTERNAL_SERVICES_IA_CACHE_QUEUE"]
        )
        self.app = app
        self.database = timescale.engine
        self.redis = cache._r
        # Cache to avoid querying same artists repeatedly 
        self.discovered_creators = set()
        self.discovered_items = set()

    def get_items_from_listen(self, listen):
        return []

    def get_items_from_seeder(self, message):
        return [JobItem(INCOMING_ITEM_PRIORITY, identifier) for identifier in message.get("ia_identifiers", [])]

    def get_seed_ids(self, limit_per_collection=1000) -> list[str]:
        """Fetch identifiers for 78rpm and cylinder collections with date filtering."""
        today = datetime.today().strftime("%Y-%m-%d")
        last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        date_filter = f"[{last_week} TO {today}]"
        
        collections = [
            {
                "name": "78rpm",
                "query": f"collection:78rpm AND mediatype:audio AND publicdate:{date_filter}"
            },
            {
                "name": "cylinder",
                "query": f"collection:cylinder AND mediatype:audio AND publicdate:{date_filter}"
            }
        ]
        identifiers = []
        for collection in collections:
            try:
                results = internetarchive.search_items(collection["query"])
                count = 0
                for item in results:
                    if count >= limit_per_collection:
                        break
                    identifier = item.get("identifier")
                    if identifier:
                        identifiers.append(identifier)
                        count += 1
                logger.info("Found %d items from %s collection", count, collection["name"])
            except Exception as e:
                logger.error("Error searching %s collection: %s", collection["name"], str(e))
        return identifiers

    def discover_items_by_creator(self, creator_name) -> list[JobItem]:
        """
        Discover more items by the same creator using IA Search API.
        
        """
        try:
            # Check cache to avoid querying same creators repeatedly
            if creator_name in self.discovered_creators:
                return []
            
            self.discovered_creators.add(creator_name)
            self.metrics["discovered_creators_count"] += 1

            # Use IA Search API to find items by creator
            query = f'creator:"{creator_name}" AND mediatype:audio'
            results = internetarchive.search_items(query)

            new_items = []
            count = 0
            for item in results:
                if count >= 50:  # Limit to prevent excessive API calls
                    break
                    
                identifier = item.get("identifier")
                if identifier and identifier not in self.discovered_items:
                    self.discovered_items.add(identifier)
                    self.metrics["discovered_items_count"] += 1
                    new_items.append(JobItem(DISCOVERED_ITEM_PRIORITY, identifier))
                    count += 1
            
            logger.info("Discovered %d items for creator: %s", count, creator_name)
            return new_items
        except Exception as e:
            logger.error("Error discovering items for creator %s: %s", creator_name, str(e), exc_info=True)
            return []

    def process(self, item_ids):
        """Process a list of IA identifiers and discover more items from creators."""
        discovered_items = []
        
        for identifier in item_ids:
            redis_key = f"ia_metadata_cache:{identifier}"
            if self.redis.get(redis_key):
                logger.debug("Skipping cached: %s", identifier)
                continue
                
            try:
                with self.database.begin() as conn:
                    # Process the item and get creator info
                    creator_names = self.process_identifier(identifier, conn)
                    self.redis.setex(redis_key, 86400, "1")
                    
                    # Discover more items by the same creators 
                    for creator_name in creator_names:
                        if creator_name and creator_name.strip():
                            discovered_items_for_creator = self.discover_items_by_creator(creator_name.strip())
                            discovered_items.extend(discovered_items_for_creator)
                            
            except Exception as e:
                logger.error("Error processing %s: %s", identifier, str(e), exc_info=True)
        
        return discovered_items

    @staticmethod
    def extract_from_description(soup: BeautifulSoup | None, field) -> str | None:
        """
        Extracts a field (e.g. 'Artist', 'Album') from the IA description HTML using BeautifulSoup.
        Handles both string and list input.
        """
        if not soup:
            return None

        for element in soup.find_all(["div", "p", "span"]):
            _text = element.get_text(strip=True)
            if _text.startswith(f"{field}:"):
                return _text[len(field) + 1:].strip()

        return None

    def process_identifier(self, identifier, conn):
        """
        Process a single identifier and return list of creator names for discovery.
        """
        try:
            item = internetarchive.get_item(identifier)
            item_metadata = item.item_metadata
            meta = item_metadata.get("metadata", {})
            files = item_metadata.get("files", [])
        except Exception as e:
            logger.error("Failed to fetch %s: %s", identifier, str(e))
            return []

        stream_urls = []
        artwork_url = None

        for f in files:
            fmt = f.get("format", "").lower()
            if any(keyword in fmt for keyword in AUDIO_KEYWORDS):
                stream_urls.append(f"https://archive.org/download/{identifier}/{f['name']}")
            if not artwork_url and fmt in {"jpeg", "jpg", "png"}:
                artwork_url = f"https://archive.org/download/{identifier}/{f['name']}"

        description = meta.get("description", "")
        if isinstance(description, list):
            description = " ".join(str(x) for x in description if x)
        try:
            soup = BeautifulSoup(description, "html.parser")
        except Exception as e:
            logger.error("Error parsing description HTML: %s", str(e))
            soup = None

        artist = meta.get("creator")
        if not artist:
            artist = self.extract_from_description(soup, "Artist")
        if isinstance(artist, str):
            artist = [artist]
        elif artist is None:
            artist = []

        album = meta.get("album")
        if not album:
            album = self.extract_from_description(soup, "Album")

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
        return artist
