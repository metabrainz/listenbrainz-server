import re

import psycopg2
from unidecode import unidecode

from mapping.utils import log
from mapping.bulk_table import BulkInsertTable
import config

TEST_ARTIST_IDS = [1160983, 49627, 65, 21238]  # Gun'n'roses, beyoncé, portishead, Erik Satie


class SpotifyMetadataIndex(BulkInsertTable):
    """
        This class creates the spotify metadata index using the reverse painters algorithm.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.spotify_metadata_index", mb_conn, lb_conn, batch_size)
        self.row_id = 0 

    def get_create_table_columns(self):
        return [("id",                               "SERIAL"),
                ("artist_ids",                       "TEXT NOT NULL"),
                ("album_id",                         "TEXT NOT NULL"),
                ("track_id",                         "TEXT NOT NULL"),
                ("combined_lookup_all",              "TEXT NOT NULL"),
                ("combined_lookup_without_album",    "TEXT NOT NULL"),
                ("score",                            "INTEGER NOT NULL")]

    def get_insert_queries(self):
        """ Retrieve the album name, track name, artist name for all tracks in spotify cache in a specific order.
        These name fields will be used to calculate a lookup for each track which will then be used for matching
        purposes. The order by determines the tie-breaking score in case of multiple rows have the same lookup.
        """
        return [("LB", """
                    SELECT album.spotify_id AS album_id
                         , album.name AS album_name
                         , album.type AS album_type
                         , album.release_date AS release_date
                         , track.spotify_id AS track_id
                         , track.name AS track_name
                         , track.track_number AS track_number
                         -- retrieve track artists in same order as they appear on the spotify track
                         , array_agg(ARRAY[artist.name, artist.spotify_id] ORDER BY rta.position) AS artists
                         -- prefer albums over single over compilations.
                         , CASE 
                            WHEN album.type = 'album' THEN 1
                            WHEN album.type = 'single' THEN 2
                            WHEN album.type = 'compilation' THEN 3
                            ELSE 4 END
                            AS album_sort_order
                      FROM spotify_cache.album album
                      JOIN spotify_cache.track track
                        ON album.spotify_id = track.album_id
                      JOIN spotify_cache.rel_track_artist rta
                        ON track.spotify_id = rta.track_id
                      JOIN spotify_cache.artist artist
                        ON rta.artist_id = artist.spotify_id
                  GROUP BY album.spotify_id
                         , album.name
                         , album.type
                         , album.release_date
                         , track.spotify_id
                         , track.name
                         , track.track_number
                  ORDER BY album_sort_order
                         , release_date
                         , album_id
                         , track_number
                         , track_name""")]

    def get_index_names(self):
        return [
            ("spotify_metadata_index_idx_combined_lookup_all", "combined_lookup_all", False),
            ("spotify_metadata_index_idx_combined_lookup_without_album", "combined_lookup_without_album", False),
        ]

    def process_row(self, row):
        """ Calculate lookup for each track and assign a score based on ordering """
        artist_names = " ".join([a[0] for a in row["artists"]])
        artist_ids = [a[1] for a in row["artists"]]
        self.row_id += 1

        combined_lookup_all = unidecode(re.sub(r'[^\w]+', '', artist_names + row["album_name"] + row["track_name"]).lower())
        combined_lookup_without_album = unidecode(re.sub(r'[^\w]+', '', artist_names + row["track_name"]).lower())

        return {"mapping.spotify_metadata_index": [
            (
                artist_ids,
                row["album_id"],
                row["track_id"],
                combined_lookup_all,
                combined_lookup_without_album,
                -self.row_id 
            )
        ]}


def create_spotify_metadata_index(use_lb_conn: bool):
    """
        Main function for creating the spotify metadata index

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """

    lb_conn = None
    if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
        lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)
    log("spotify_metdata_index: start!")

    ndx = SpotifyMetadataIndex(None, lb_conn)
    ndx.run()

    log("spotify_metdata_index: done!")
