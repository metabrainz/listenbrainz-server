import re

import psycopg2
from psycopg2.errors import OperationalError
from unidecode import unidecode

from mapping.utils import log
from mapping.custom_sorts import create_custom_sort_tables
from mapping.bulk_table import BulkInsertTable
from mapping.canonical_recording_redirect import CanonicalRecordingRedirect
from mapping.canonical_release_redirect import CanonicalReleaseRedirect
from mapping.canonical_musicbrainz_data_release import CanonicalMusicBrainzDataRelease
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
        return [("id",                 "SERIAL"),
                ("artist_ids",         "TEXT NOT NULL"),
                ("artist_names",       "TEXT NOT NULL"),
                ("album_id",           "TEXT NOT NULL"),
                ("album_name",         "TEXT NOT NULL"),
                ("track_id",           "TEXT NOT NULL"),
                ("track_name",         "TEXT NOT NULL"),
                ("combined_lookup",    "TEXT NOT NULL"),
                ("score",              "INTEGER NOT NULL")]

    def get_insert_queries(self):
        return [("LB", """SELECT data->>'release_date'
                               , data->>'album_type'
                               , data->>'id' AS album_id
                               , data->>'name' AS album_name
                               , tracks->>'track_number' AS track_num
                               , tracks->>'id' AS track_id
                               , tracks->>'name' AS track_name
                               , array_agg(ARRAY[artists->>'name', artists->>'id']) AS artists
                            FROM mapping.spotify_metadata_cache,
                                 jsonb_array_elements(data->'tracks') tracks,
                                 jsonb_array_elements(tracks->'artists') artists
                        GROUP BY data->>'release_date'
                               , data->>'album_type'
                               , data->>'id'
                               , data->>'id'
                               , data->>'name'
                               , tracks->>'id'
                               , tracks->>'track_number'
                               , tracks->>'name'
                        ORDER BY data->>'release_date', data->>'album_type', album_id,
                                 CAST(tracks->>'track_number' AS INTEGER), tracks->>'name'""")]

    def get_index_names(self):
        return [
            ("spotify_metadata_index_idx_combined_lookup", "combined_lookup", False),
            ("spotify_metadata_index_idx_artist_track_name", "artist_names, track_name", False)
        ]

    def process_row(self, row):

        artist_names = " ".join([ a[0] for a in row["artists"]])
        artist_ids = [ a[1] for a in row["artists"] ]
        self.row_id += 1

        combined_lookup = unidecode(re.sub(r'[^\w]+', '', artist_names + row["album_name"] + row['track_name']).lower())
        return {"mapping.spotify_metadata_index": [
            (
                artist_ids,
                artist_names,
                row["album_id"],
                row["album_name"],
                row["track_id"],
                row["track_name"],
                combined_lookup,
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

    ndx = SpotifyMetadataIndex(None, lb_conn)
    ndx.run()

    log("spotify_metdata_index: done!")
