from flask import current_app
from kombu import Connection, Exchange
from kombu.entity import PERSISTENT_DELIVERY_MODE
from spotipy import SpotifyClientCredentials, Spotify

from listenbrainz.utils import get_fallback_connection_name


def get_album_ids():
    """ Retrieve spotify album ids from new releases for all markets"""
    sp = Spotify(auth_manager=SpotifyClientCredentials(
        client_id=current_app.config["SPOTIFY_CLIENT_ID"],
        client_secret=current_app.config["SPOTIFY_CLIENT_SECRET"]
    ))
    markets = sp.available_markets()["markets"]

    album_ids = set()
    for market in markets:
        result = sp.new_releases(market, limit=50)
        album_ids |= {album["id"] for album in result["albums"]["items"]}

        while result.get("next"):
            result = sp.next(result)
            album_ids |= {album["id"] for album in result["albums"]["items"]}

    return album_ids


def submit_album_ids(album_ids):
    """ Submit album ids to seed spotify metadata cache """
    message = {"spotify_album_ids": list(album_ids)}
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
        routing_key=current_app.config["EXTERNAL_SERVICES_SPOTIFY_CACHE_QUEUE"],
        exchange=exchange,
        delivery_mode=PERSISTENT_DELIVERY_MODE,
        declare=[exchange]
    )


def submit_new_releases_to_cache():
    """ Query spotify new releases for album ids and submit those to spotify metadata cache """
    current_app.logger.info("Searching new album ids to seed spotify metadata cache")
    album_ids = get_album_ids()
    current_app.logger.info("Found %d album ids", len(album_ids))
    submit_album_ids(album_ids)
    current_app.logger.info("Submitted new release album ids")
