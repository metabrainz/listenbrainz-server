import logging
import time
import re
import pika
from html import unescape
from sqlalchemy import text
import internetarchive
from listenbrainz.webserver import create_app
from brainzutils import cache
from listenbrainz.db import timescale
from listenbrainz import  config
from listenbrainz.webserver.redis_connection import init_redis_connection
from listenbrainz.metadata_cache.internetarchive.models import InternetArchiveTrack


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


redis_client = init_redis_connection(logger)

def ensure_str(val):
    if isinstance(val, list):
        return " ".join(str(x) for x in val)
    if val is None:
        return ""
    return str(val)

def extract_metadata_from_html(notes, field):
    pattern = rf"{field}:\s*(.*?)<"
    match = re.search(pattern, notes, re.IGNORECASE)
    if match:
        return unescape(match.group(1)).strip()
    return ""

def process_identifier(identifier, conn):
    """Process a single Internet Archive identifier"""

    redis_key = f"ia_metadata_cache:{identifier}"
    
    if redis_client.get(redis_key):  #  Using redis_client
        logger.info(f"Skipping cached item: {identifier}")
        return

    try:
        ia_item = internetarchive.get_item(identifier)
        files = list(ia_item.get_files())
    except Exception as e:
        logger.error(f"Error fetching files for {identifier}: {e}")
        return

    if not files:
        logger.info(f"No files found for item: {identifier}")
        return

    count = 0
    for file in files:
        fmt = file.format.lower() if hasattr(file, 'format') and file.format else ''
        name = file.name
        if fmt.endswith(('mp3', 'ogg', 'wav', 'flac')):
            audio_url = f"https://archive.org/download/{identifier}/{name}"

            # Check TimescaleDB
            exists = conn.execute(
                text("SELECT 1 FROM metadata_cache.internetarchive WHERE id = :id"),
                {"id": audio_url}
            ).fetchone()

            if exists:
                redis_client.setex(redis_key, 86400, "1")  #  Using redis_client
                continue

            meta = ia_item.metadata

            title = ensure_str(meta.get('title'))
            creator = ensure_str(meta.get('creator'))
            album = ensure_str(meta.get('album')) or ensure_str(meta.get('label'))
            year = ensure_str(meta.get('year')) or ensure_str(meta.get('date'))
            notes = ensure_str(meta.get('notes')) or ensure_str(meta.get('description'))
            topics = ensure_str(meta.get('subject'))

            # Fallback title extraction
            if not title:
                base_name = name.rsplit('.', 1)[0]
                base_name = re.sub(r'^\d+\s*', '', base_name)
                title = base_name

            # Extract from notes if needed
            if not creator and notes:
                creator = extract_metadata_from_html(notes, "Artist")
            if not album and notes:
                album = extract_metadata_from_html(notes, "Album")
            if not year and notes:
                year = extract_metadata_from_html(notes, "Year")

            track = InternetArchiveTrack(
                id=identifier,
                title=title,
                creator=creator,
                album=album,
                year=year,
                notes=notes,
                topics=topics,
                stream_url=audio_url,
                duration=None,
                artwork_url=None,
                date=year
            )

            # Insert into TimescaleDB
            conn.execute(
                text("""
                    INSERT INTO metadata_cache.internetarchive (id, data, last_updated)
                    VALUES (:id, :data, NOW())
                    ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, last_updated = NOW()
                """),
                {"id": audio_url, "data": track.json()}
            )

            redis_client.setex(redis_key, 86400, "1")  #  Using redis_client
            count += 1
            logger.info(f"Added: {audio_url}")

    logger.info(f"Processed {count} files for {identifier}")


def start_consumer():
    """Main RabbitMQ consumer loop"""
    try:
        rabbitmq_params = pika.ConnectionParameters(
        host=getattr(config, 'RABBITMQ_HOST', 'rabbitmq'),
        port=getattr(config, 'RABBITMQ_PORT', 5672),
        virtual_host=getattr(config, 'RABBITMQ_VHOST', '/'),
        credentials=pika.PlainCredentials(
        getattr(config, 'RABBITMQ_USERNAME', 'guest'),
        getattr(config, 'RABBITMQ_PASSWORD', 'guest')
            )
        )
        connection = pika.BlockingConnection(rabbitmq_params)

        channel = connection.channel()
        channel.queue_declare(queue='ia_metadata_seed', durable=True)
        logger.info(" [*] Waiting for messages. To exit press CTRL+C")

        def callback(ch, method, properties, body):
            try:
                identifier = body.decode('utf-8')
                logger.info(f"Processing {identifier}")
                
                with timescale.engine.begin() as conn:
                    process_identifier(identifier, conn)
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Error processing {body}: {e}", exc_info=True)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(
            queue='ia_metadata_seed',
            on_message_callback=callback,
            auto_ack=False
        )
        channel.start_consuming()
    except Exception as e:
        logger.error(f"RabbitMQ connection error: {e}", exc_info=True)
        raise

def fetch_and_store_ia_metadata():
    logger.info("Starting Internet Archive indexer...")
    start_consumer()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        fetch_and_store_ia_metadata()
