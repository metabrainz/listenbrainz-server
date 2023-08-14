from flask import current_app
from kombu import Connection, Exchange
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.apple_metadata_cache.apple import Apple
from listenbrainz.utils import get_fallback_connection_name


def get_album_ids():
    """ Retrieve apple album ids from new releases for all markets"""
    client = Apple()
    storefronts = client.get("https://api.music.apple.com/v1/storefronts")
    album_ids = set()
    for storefront in storefronts:
        response = client.get(f"https://api.music.apple.com/v1/catalog/{storefront}/charts", {
            "types": "albums",
            "limit": 200
        })
        album_ids |= {album["id"] for album in response["results"]["albums"][0]["data"]}
    return album_ids


def submit_album_ids(album_ids):
    """ Submit album ids to seed apple metadata cache """
    message = {"apple_album_ids": list(album_ids)}
    connection = Connection(
        hostname=current_app.config["RABBITMQ_HOST"],
        userid=current_app.config["RABBITMQ_USERNAME"],
        port=current_app.config["RABBITMQ_PORT"],
        password=current_app.config["RABBITMQ_PASSWORD"],
        virtual_host=current_app.config["RABBITMQ_VHOST"],
        transport_options={"client_properties": {"connection_name": get_fallback_connection_name()}}
    )
    producer = connection.Producer()
    exchange = Exchange(current_app.config["EXTERNAL_SERVICES_EXCHANGE"], "topic", durable=True)
    producer.publish(
        message,
        routing_key=current_app.config["EXTERNAL_SERVICES_APPLE_CACHE_QUEUE"],
        exchange=exchange,
        delivery_mode=PERSISTENT_DELIVERY_MODE,
        declare=[exchange]
    )


def submit_new_releases_to_cache():
    """ Query apple new releases for album ids and submit those to apple metadata cache """
    current_app.logger.info("Searching new album ids to seed apple metadata cache")
    album_ids = get_album_ids()
    current_app.logger.info("Found %d album ids", len(album_ids))
    submit_album_ids(album_ids)
    current_app.logger.info("Submitted new release album ids")
