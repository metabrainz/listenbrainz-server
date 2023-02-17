import re

import psycopg2
from psycopg2.errors import OperationalError
from unidecode import unidecode

from mapping.utils import log
from mapping.custom_sorts import create_custom_sort_tables
from mapping.bulk_table import BulkInsertTable
from mapping.canonical_recording_redirect import CanonicalRecordingRedirect
from mapping.canonical_recording_release_redirect import CanonicalRecordingReleaseRedirect
from mapping.canonical_release_redirect import CanonicalReleaseRedirect
from mapping.canonical_release import CanonicalRelease

import config

TEST_ARTIST_IDS = [1160983, 49627, 65, 21238]  # Gun'n'roses, beyoncé, portishead, Erik Satie


class CanonicalMusicBrainzDataBase(BulkInsertTable):
    """
        This class creates the MBID mapping tables.

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def get_create_table_columns(self):
        return [("id",                 "SERIAL"),
                ("artist_credit_id",   "INT NOT NULL"),
                ("artist_mbids",       "UUID[] NOT NULL"),
                ("artist_credit_name", "TEXT NOT NULL"),
                ("release_mbid",       "UUID NOT NULL"),
                ("release_name",       "TEXT NOT NULL"),
                ("recording_mbid",     "UUID NOT NULL"),
                ("recording_name",     "TEXT NOT NULL"),
                ("combined_lookup",    "TEXT NOT NULL"),
                ("score",              "INTEGER NOT NULL"),
                ("year",               "INTEGER")]

    def get_insert_queries(self):
        return [("MB", """
               SELECT ac.id as artist_credit_id
                    , r.name AS recording_name
                    , r.gid AS recording_mbid
                    , ac.name AS artist_credit_name
                    , s.artist_mbids
                    , rl.name AS release_name
                    , rl.gid AS release_mbid
                    , rpr.id AS score
                    , date_year AS year
                 FROM musicbrainz.recording r
                 JOIN musicbrainz.artist_credit ac
                   ON r.artist_credit = ac.id
                 JOIN musicbrainz.artist_credit_name acn
                   ON ac.id = acn.artist_credit
                 JOIN musicbrainz.artist a
                   ON acn.artist = a.id
                 JOIN musicbrainz.track t
                   ON t.recording = r.id
                 JOIN musicbrainz.medium m
                   ON m.id = t.medium
                 JOIN musicbrainz.release rl
                   ON rl.id = m.release
                 JOIN mapping.canonical_release_tmp rpr
                   ON rl.id = rpr.release
                 JOIN (SELECT artist_credit, array_agg(gid ORDER BY position) AS artist_mbids
                         FROM musicbrainz.artist_credit_name acn2
                         JOIN musicbrainz.artist a2
                           ON acn2.artist = a2.id
                     GROUP BY acn2.artist_credit) s
                   ON acn.artist_credit = s.artist_credit
            LEFT JOIN musicbrainz.release_country rc
                   ON rc.release = rl.id
             GROUP BY rpr.id, ac.id, s.artist_mbids, rl.gid, artist_credit_name, r.gid, r.name, release_name, year
             ORDER BY ac.id, rpr.id
        """)]

    def get_index_names(self):
        table = self.table_name.split(".")[-1]
        return [
            (f"{table}_idx_combined_lookup",              "combined_lookup", False),
            (f"{table}_idx_artist_credit_recording_name_release_name", "artist_credit_name, recording_name, release_name", False),
            (f"{table}_idx_recording_mbid", "recording_mbid", True)
        ]

    def get_combined_lookup(self, row):
        pass

    def process_row(self, row):
        combined_lookup = self.get_combined_lookup(row)
        return {
            self.table_name: [(
                row["artist_credit_id"],
                row["artist_mbids"],
                row["artist_credit_name"],
                row["release_mbid"],
                row["release_name"],
                row["recording_mbid"],
                row["recording_name"],
                combined_lookup,
                row["score"],
                row["year"]
            )]
        }



def create_canonical_musicbrainz_data(use_lb_conn: bool):
    """
        Main function for creating the MBID mapping and its related tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """
    mb_uri = config.MB_DATABASE_MASTER_URI or config.MBID_MAPPING_DATABASE_URI

    with psycopg2.connect(mb_uri) as mb_conn:

        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)

        # Setup all the needed objects
        can = CanonicalRecordingRedirect(mb_conn, lb_conn)
        can_rec_rel = CanonicalRecordingReleaseRedirect(mb_conn, lb_conn)
        can_rel = CanonicalReleaseRedirect(mb_conn)
        releases = CanonicalRelease(mb_conn)
        mapping = CanonicalMusicBrainzData(mb_conn, lb_conn)
        mapping.add_additional_bulk_table(can)

        # Carry out the bulk of the work
        create_custom_sort_tables(mb_conn)
        releases.run(no_swap=True)
        mapping.run(no_swap=True)
        can_rec_rel.run(no_swap=True)
        can_rel.run(no_swap=True)

        # Now swap everything into production in a single transaction
        log("canonical_musicbrainz_data: Swap into production")
        if lb_conn:
            releases.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mapping.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can_rec_rel.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can_rel.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mb_conn.commit()
            lb_conn.commit()
            lb_conn.close()
        else:
            releases.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mapping.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can_rec_rel.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can_rel.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mb_conn.commit()

        log("canonical_musicbrainz_data: done done done!")
