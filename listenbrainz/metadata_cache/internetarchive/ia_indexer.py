import logging
import time
import internetarchive
from listenbrainz.webserver import create_app
from listenbrainz.db import timescale
from listenbrainz.metadata_cache.soundcloud.models import SoundcloudTrack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_and_store_ia_metadata(limit_per_collection=1000, sleep_seconds=1):
    logger.info("Starting Internet Archive indexer...")

    # Define our search queries
    search_queries = [
        {'name': '78rpm', 'query': 'collection:78rpm AND mediatype:audio'},
        {'name': 'cylinder_recordings', 'query': 'cylinder mediatype:audio'}
    ]

    total_count = 0
    with timescale.engine.begin() as conn:  # Use context manager for connection
        for search_item in search_queries:
            query_name = search_item['name']
            query = search_item['query']

            print(f"\nIndexing: {query_name} with query: {query}")
            results = internetarchive.search_items(query)
            count = 0

            for item in results:
                if count >= limit_per_collection:
                    print(f"  Reached limit of {limit_per_collection} for {query_name}.")
                    break  # Move to the next collection

                identifier = item.get('identifier')
                print(f"Checking item: {identifier}")
                try:
                    ia_item = internetarchive.get_item(identifier)
                    files = list(ia_item.get_files())
                except Exception as e:
                    print(f"  Error fetching files for {identifier}: {e}")
                    continue

                if not files:
                    print(f"  No files found for item: {identifier}")
                    continue

                for file in files:
                    fmt = file.format.lower() if hasattr(file, 'format') and file.format else ''
                    name = file.name
                    if fmt.endswith(('mp3', 'ogg', 'wav', 'flac')):
                        audio_url = f"https://archive.org/download/{identifier}/{name}"

                        # Check if already exists in Timescale/Postgres
                        exists = conn.execute(
                            "SELECT 1 FROM metadata_cache.internetarchive WHERE id = %s",
                            (audio_url,)
                        ).fetchone()
                        if exists:
                            continue

                        # Prepare data as JSON (SoundCloudTrack is used as a convenient schema)
                        track = SoundCloudTrack(
                            id=identifier,
                            title=item.get('title', ''),
                            artist=item.get('creator', ''),
                            stream_url=audio_url,
                            duration=None,  # can extract duration if available
                            artwork_url=None,  # can extract artwork if available
                            date=item.get('date', '')
                        )

                        # Insert into Timescale/Postgres
                        conn.execute(
                            """
                            INSERT INTO metadata_cache.internetarchive (id, data, last_updated)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, last_updated = NOW()
                            """,
                            (audio_url, track.json())
                        )
                        count += 1
                        total_count += 1
                        print(f"  Added: {audio_url}")
                        if count % 10 == 0:
                            print(f"  Progress: {count} tracks added in {query_name}...")

                time.sleep(sleep_seconds)  # To be nice to the API
            print(f"Completed {query_name} with {count} items.")
    print(f"\nFinished indexing. Total recordings added: {total_count}")
    logger.info("Indexing complete!")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        fetch_and_store_ia_metadata(limit_per_collection=1000, sleep_seconds=1)
