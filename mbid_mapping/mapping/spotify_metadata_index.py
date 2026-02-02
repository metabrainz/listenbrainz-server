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

    lb_conn = None
    if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
        lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)
    log("spotify_metadata_index: start!")

    ndx = AlbumMetadataIndex("spotify", "spotify_cache", lb_conn)
    ndx.run()

    log("spotify_metadata_index: done!")
