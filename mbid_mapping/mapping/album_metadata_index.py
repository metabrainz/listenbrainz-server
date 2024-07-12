import abc
import re

from unidecode import unidecode

from mapping.bulk_table import BulkInsertTable



class AlbumMetadataIndex(BulkInsertTable, abc.ABC):
    """
        This class creates the metadata index for external music services, that support albums,
        using the reverse painters' algorithm.
    """

    def __init__(self, name, schema, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__(f"mapping.{name}_metadata_index", select_conn, insert_conn, batch_size, unlogged)
        self.name = name
        self.row_id = 0
        self.schema = schema

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
        return [f"""
            SELECT album.album_id AS album_id
                 , album.name AS album_name
                 , album.type AS album_type
                 , album.release_date AS release_date
                 , track.track_id AS track_id
                 , track.name AS track_name
                 , track.track_number AS track_number
                 -- retrieve track artists in same order as they appear on the spotify track
                 , array_agg(ARRAY[artist.name, artist.artist_id] ORDER BY rta.position) AS artists
                 -- prefer albums over single over compilations.
                 , CASE 
                    WHEN album.type = 'album' THEN 1
                    WHEN album.type = 'single' THEN 2
                    WHEN album.type = 'compilation' THEN 3
                    ELSE 4 END
                    AS album_sort_order
              FROM {self.schema}.album album
              JOIN {self.schema}.track track
                ON album.album_id = track.album_id
              JOIN {self.schema}.rel_track_artist rta
                ON track.track_id = rta.track_id
              JOIN {self.schema}.artist artist
                ON rta.artist_id = artist.artist_id
          GROUP BY album.album_id
                 , album.name
                 , album.type
                 , album.release_date
                 , track.track_id
                 , track.name
                 , track.track_number
          ORDER BY album_sort_order
                 , release_date
                 , album_id
                 , track_number
                 , track_name
        """]

    def get_index_names(self):
        return [
            (f"{self.name}_metadata_index_idx_combined_lookup_all", "combined_lookup_all", False),
            (f"{self.name}_metadata_index_idx_combined_lookup_without_album", "combined_lookup_without_album", False),
        ]

    def process_row(self, row):
        """ Calculate lookup for each track and assign a score based on ordering """
        artist_names = " ".join([a[0] for a in row["artists"]])
        artist_ids = [a[1] for a in row["artists"]]
        self.row_id += 1

        combined_lookup_all = unidecode(re.sub(r'[^\w]+', '', artist_names + row["album_name"] + row["track_name"]).lower())
        combined_lookup_without_album = unidecode(re.sub(r'[^\w]+', '', artist_names + row["track_name"]).lower())

        return {f"mapping.{self.name}_metadata_index": [
            (
                artist_ids,
                row["album_id"],
                row["track_id"],
                combined_lookup_all,
                combined_lookup_without_album,
                -self.row_id
            )
        ]}
