import logging
import json
from kombu.mixins import ConsumerMixin
from kombu import Connection, Queue, Exchange
from sqlalchemy import text
import internetarchive
from bs4 import BeautifulSoup
from brainzutils import cache
from listenbrainz import config
from listenbrainz.webserver import create_app
from listenbrainz.db import timescale
from listenbrainz.webserver.rabbitmq_connection import init_rabbitmq_connection

logger = logging.getLogger(__name__)

# Comprehensive list of audio format keywords
AUDIO_KEYWORDS = [
    "mp3", "ogg", "vorbis", "flac", "wav", "aiff", "apple lossless", "m4a", "opus", "aac",
    "au", "wma", "alac", "ape", "shn", "tta", "wv", "mpc", "aifc", "m4b", "m4p", "vbr", 
    "m3u", "cylinder", "78rpm", "lossless", "lossy", "webm", "aif", "mid", "midi", "amr",
    "ra", "rm", "vox", "dts", "ac3", "atrac", "pcm", "adpcm", "gsm", "mmf", "3ga", "8svx"
]

def extract_from_description(description, field):
    """
    Extracts a field (e.g. 'Artist', 'Album') from the IA description HTML using BeautifulSoup.
    """
    if not description:
        return None
    try:
        soup = BeautifulSoup(description, "html.parser")
        for element in soup.find_all(['div', 'p', 'span']):
            text = element.get_text(strip=True)
            if text.startswith(f"{field}:"):
                return text[len(field)+1:].strip()
    except Exception as e:
        logger.error("Error parsing description HTML: %s", str(e))
    return None

class InternetArchiveIndexer(ConsumerMixin):
    def __init__(self, app):
        init_rabbitmq_connection(app)
        self.database = timescale.engine
        self.redis = cache._r
        self.app = app

    @property
    def connection(self):
        return Connection(
            hostname=self.app.config["RABBITMQ_HOST"],
            userid=self.app.config["RABBITMQ_USERNAME"],
            port=self.app.config["RABBITMQ_PORT"],
            password=self.app.config["RABBITMQ_PASSWORD"],
            virtual_host=self.app.config["RABBITMQ_VHOST"]
        )

    def get_consumers(self, Consumer, channel):
        ia_queue = Queue(
            'ia_metadata_seed',
            Exchange(config.EXTERNAL_SERVICES_EXCHANGE, type='topic', durable=False),
            routing_key='ia_metadata_seed',
            durable=True
        )
        return [Consumer(
            queues=[ia_queue],
            callbacks=[self.process_message],
            accept=['json']
        )]

    def process_message(self, body, message):
        if isinstance(body, str):
            if not body.strip():
                logger.error("Received empty message body, skipping.")
                message.ack()
                return
            try:
                body = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON body: {body!r} error: {e}")
                message.reject()
                return

        identifier = body.get('identifier')
        if not identifier:
            logger.error("No 'identifier' in message body, skipping.")
            message.ack()
            return

        redis_key = f"ia_metadata_cache:{identifier}"

        if self.redis.get(redis_key):
            logger.info("Skipping cached: %s", identifier)
            message.ack()
            return

        try:
            with self.database.begin() as conn:
                self.process_identifier(identifier, conn)
                self.redis.setex(redis_key, 86400, "1")
            message.ack()
        except Exception as e:
            logger.error("Error processing %s: %s", identifier, str(e), exc_info=True)
            message.reject()

    def process_identifier(self, identifier, conn):
        try:
            item = internetarchive.get_item(identifier)
            item_metadata = item.item_metadata
            meta = item_metadata.get("metadata", {})
            files = item_metadata.get("files", [])
        except Exception as e:
            logger.error("Failed to fetch %s: %s", identifier, str(e))
            raise

        # Collect all playable audio file URLs for the whole item
        stream_urls = []
        artwork_url = None
        audio_file_count = 0
        
        for f in files:
            fmt = f.get("format", "").lower()
            
            # Check if any audio keyword is in the format string
            if any(keyword in fmt for keyword in AUDIO_KEYWORDS):
                stream_urls.append(f"https://archive.org/download/{identifier}/{f['name']}")
                audio_file_count += 1
                
            # Check for artwork
            if not artwork_url and fmt in {"jpeg", "jpg", "png"}:
                artwork_url = f"https://archive.org/download/{identifier}/{f['name']}"

        # Extract artist with fallback to description parsing
        artist = meta.get("creator")
        if not artist:
            artist = extract_from_description(meta.get("description", ""), "Artist")
        if isinstance(artist, str):
            artist = [artist]
        elif artist is None:
            artist = []

        # Extract album with fallback to description parsing
        album = meta.get("album")
        if not album:
            album = extract_from_description(meta.get("description", ""), "Album")

        # Prepare the track object
        track = {
            "track_id": f"https://archive.org/details/{identifier}",
            "name": meta.get("title", ""),
            "artist": artist,
            "album": album,
            "stream_urls": stream_urls,
            "artwork_url": artwork_url,
            "data": meta,
        }

        # Upsert into DB
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
                "track_id": track["track_id"],
                "name": track["name"],
                "artist": track["artist"],
                "album": track["album"],
                "stream_urls": track["stream_urls"],
                "artwork_url": track["artwork_url"],
                "data": json.dumps(track["data"]),
            }
        )
        logger.info("Processed and stored metadata for %s (%d audio files found)", identifier, audio_file_count)

def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting IA Indexer...")
    app = create_app()
    try:
        InternetArchiveIndexer(app).run()
    except KeyboardInterrupt:
        logger.info("Stopping IA Indexer")
    except Exception as e:
        logger.error("Indexer failed: %s", str(e), exc_info=True)
        raise

if __name__ == '__main__':
    main()
