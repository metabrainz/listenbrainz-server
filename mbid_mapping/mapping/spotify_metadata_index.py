import psycopg2

from mapping.album_metadata_index import AlbumMetadataIndex
from mapping.utils import log
import config


def create_spotify_metadata_index(use_lb_conn: bool):
    """
        Main function for creating the spotify metadata index

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """

    cache_conn = None
    listens_conn = None
    if use_lb_conn and config.SQLALCHEMY_LISTENS_URI:
        cache_conn = psycopg2.connect(config.SQLALCHEMY_LISTENS_URI)
        listens_conn = psycopg2.connect(config.SQLALCHEMY_LISTENS_URI)
    log("spotify_metadata_index: start!")

    ndx = AlbumMetadataIndex("spotify", "spotify_cache", cache_conn, listens_conn)
    ndx.run()

    log("spotify_metadata_index: done!")
