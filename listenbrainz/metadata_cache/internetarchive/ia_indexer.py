import logging
import re
import json
from html import unescape
from kombu.mixins import ConsumerMixin
from kombu import Connection, Queue, Exchange
from sqlalchemy import text
import internetarchive
from brainzutils import cache
from listenbrainz import config
from listenbrainz.webserver import create_app
from listenbrainz.db import timescale
from listenbrainz.metadata_cache.internetarchive.models import InternetArchiveTrack
from listenbrainz.webserver.rabbitmq_connection import init_rabbitmq_connection

logger = logging.getLogger(__name__)

class InternetArchiveIndexer(ConsumerMixin):
    def __init__(self, app):
        # Initialize RabbitMQ connection pools and exchanges
        init_rabbitmq_connection(app)
        self.database = timescale.engine
        self.redis = cache._r
        self.app = app

    @property
    def connection(self):
        # Kombu's ConsumerMixin expects this property to return a valid kombu.Connection
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
            files = list(item.get_files())
        except Exception as e:
            logger.error("Failed to fetch %s: %s", identifier, str(e))
            raise

        count = 0
        for file in files:
            if self.process_file(file, identifier, conn):
                count += 1

        logger.info("Processed %d files from %s", count, identifier)

    def process_file(self, file, identifier, conn):
        if not self.is_audio_file(file):
            return False

        audio_url = f"https://archive.org/download/{identifier}/{file.name}"
        if self.exists_in_db(conn, audio_url):
            return False

        track = self.create_track(identifier, file.name, audio_url, file.item.metadata)
        self.store_in_db(conn, audio_url, track)
        return True

    def is_audio_file(self, file):
        fmt = file.format.lower() if file.format else ''
        return fmt.endswith(('mp3', 'ogg', 'wav', 'flac'))

    def exists_in_db(self, conn, audio_url):
        return conn.execute(
            text("SELECT 1 FROM metadata_cache.internetarchive WHERE id = :id"),
            {'id': audio_url}
        ).fetchone()

    def store_in_db(self, conn, audio_url, track):
        conn.execute(
            text("""
                INSERT INTO metadata_cache.internetarchive (id, data, last_updated)
                VALUES (:id, :data, NOW())
                ON CONFLICT (id) DO UPDATE 
                SET data = EXCLUDED.data, last_updated = NOW()
            """),
            {'id': audio_url, 'data': track.json()}
        )

    def create_track(self, identifier, filename, audio_url, meta):
        title = self.ensure_str(meta.get('title')) or self.extract_from_filename(filename)
        creator = self.ensure_str(meta.get('creator'))
        album = self.ensure_str(meta.get('album')) or self.ensure_str(meta.get('label'))
        year = self.ensure_str(meta.get('year')) or self.ensure_str(meta.get('date'))
        notes = self.ensure_str(meta.get('notes')) or self.ensure_str(meta.get('description'))
        topics = self.ensure_str(meta.get('subject'))  # 'subject' is the key for topics in IA metadata

        # Fallback extraction from notes if missing
        if not creator and notes:
            creator = self.extract_metadata_from_html(notes, "Artist")
        if not album and notes:
            album = self.extract_metadata_from_html(notes, "Album")
        if not year and notes:
            year = self.extract_metadata_from_html(notes, "Year")

        # Optionally set duration and artwork_url if available in meta
        duration = meta.get('length') or None  # IA sometimes uses 'length'
        artwork_url = meta.get('image') if meta.get('image') else None

        return InternetArchiveTrack(
            id=identifier,
            title=title,
            creator=creator,
            album=album,
            year=year,
            notes=notes,
            topics=topics,
            stream_url=audio_url,
            duration=duration,
            artwork_url=artwork_url,
            date=year
        )

    @staticmethod
    def ensure_str(val):
        if isinstance(val, list):
            return " ".join(str(x) for x in val)
        return str(val) if val else ""

    @staticmethod
    def extract_metadata_from_html(notes, field):
        pattern = rf"{field}:\s*(.*?)<"
        match = re.search(pattern, notes, re.IGNORECASE)
        if match:
            return unescape(match.group(1)).strip()
        return ""

    @staticmethod
    def extract_from_filename(filename):
        base = filename.rsplit('.', 1)[0]
        return re.sub(r'^\d+\s*', '', base)

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
