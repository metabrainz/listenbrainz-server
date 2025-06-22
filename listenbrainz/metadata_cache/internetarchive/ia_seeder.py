import logging
import time
from kombu import Connection, Exchange, Producer
import internetarchive
from listenbrainz import config

logger = logging.getLogger(__name__)

def fetch_and_seed_collections(limit_per_collection=1000, sleep_seconds=1):
    """Fetch collection identifiers and seed them to RabbitMQ"""
    logger.info("Starting Internet Archive seeder...")

    collections = [
        {'name': '78rpm', 'query': 'collection:78rpm AND mediatype:audio'},
        {'name': 'cylinder', 'query': 'cylinder mediatype:audio'}
    ]

    exchange = Exchange(config.EXTERNAL_SERVICES_EXCHANGE, 'topic', durable=False)

    with Connection(
        hostname=config.RABBITMQ_HOST,
        port=config.RABBITMQ_PORT,
        userid=config.RABBITMQ_USERNAME,
        password=config.RABBITMQ_PASSWORD,
        virtual_host=config.RABBITMQ_VHOST
    ) as connection:
        producer = Producer(connection)

        for collection in collections:
            logger.info("Seeding collection: %s", collection['name'])
            results = internetarchive.search_items(collection['query'])

            count = 0
            for item in results:
                if count >= limit_per_collection:
                    break

                identifier = item.get('identifier')
                if not identifier:
                    continue

                producer.publish(
                    {'identifier': identifier},
                    exchange=exchange,
                    routing_key='ia_metadata_seed',
                    declare=[exchange],
                    serializer='json'
                )
                count += 1
                logger.info("Published identifier %s (%d/%d) to queue", identifier, count, limit_per_collection)
                time.sleep(sleep_seconds)

            logger.info("Seeded %d items from %s", count, collection['name'])

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    fetch_and_seed_collections()
