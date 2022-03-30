import re

import psycopg2
from psycopg2.errors import OperationalError
from unidecode import unidecode

from mapping.utils import create_schema, insert_rows, log
from mapping.formats import create_formats_table
from mapping.bulk_table import BulkInsertTable
from mapping.canonical_recordings import CanonicalRecordings
from mapping.canonical_releases import CanonicalReleases
from mapping.mbid_mapping_releases import MBIDMappingReleases
import config

TEST_ARTIST_IDS = [1160983, 49627, 65, 21238]  # Gun'n'roses, beyoncé, portishead, Erik Satie


class MBIDMapping(BulkInsertTable):
    """
        This class creates the MBID mapping tables.

        For documentation on what each of the functions in this class does, please refer
        to the BulkInsertTable docs.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.mbid_mapping", mb_conn, lb_conn, batch_size)
        self.last_artist_credit_id = None
        self.artist_recordings = {}

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
                 FROM recording r
                 JOIN artist_credit ac
                   ON r.artist_credit = ac.id
                 JOIN artist_credit_name acn
                   ON ac.id = acn.artist_credit
                 JOIN artist a
                   ON acn.artist = a.id
                 JOIN track t
                   ON t.recording = r.id
                 JOIN medium m
                   ON m.id = t.medium
                 JOIN release rl
                   ON rl.id = m.release
                 JOIN mapping.mbid_mapping_releases_tmp rpr
                   ON rl.id = rpr.release
                 JOIN (SELECT artist_credit, array_agg(gid) AS artist_mbids
                         FROM artist_credit_name acn2
                         JOIN artist a2
                           ON acn2.artist = a2.id
                     GROUP BY acn2.artist_credit) s
                   ON acn.artist_credit = s.artist_credit
            LEFT JOIN release_country rc
                   ON rc.release = rl.id
             GROUP BY rpr.id, ac.id, s.artist_mbids, rl.gid, artist_credit_name, r.gid, r.name, release_name, year
             ORDER BY ac.id, rpr.id
        """)]

    def get_post_process_queries(self):
        return ["""
            WITH all_recs AS (
                SELECT *
                     , row_number() OVER (PARTITION BY combined_lookup ORDER BY score) AS rnum
                  FROM mapping.mbid_mapping_tmp
            ), deleted_recs AS (
                DELETE
                  FROM mapping.mbid_mapping_tmp
                 WHERE id IN (SELECT id FROM all_recs WHERE rnum > 1)
             RETURNING recording_mbid, combined_lookup
            )
           INSERT INTO mapping.canonical_recording_tmp (recording_mbid, canonical_recording_mbid, canonical_release_mbid)
                SELECT t1.recording_mbid
                     , t2.recording_mbid AS canonical_recording
                     , t2.release_mbid AS canonical_release
                  FROM deleted_recs t1
                  JOIN all_recs t2
                    ON t1.combined_lookup = t2.combined_lookup
                 WHERE t2.rnum = 1;
        """]

    def get_index_names(self):
        return [("mbid_mapping_idx_combined_lookup",              "combined_lookup", False),
                ("mbid_mapping_idx_artist_credit_recording_name", "artist_credit_name, recording_name", False)]

    def process_row(self, row):

        result = []
        canonical_recording_result = []

        if not self.last_artist_credit_id:
            self.last_artist_credit_id = row['artist_credit_id']

        if row['artist_credit_id'] != self.last_artist_credit_id:
            result = self.artist_recordings.values()
            self.artist_recordings = {}

        combined_lookup = unidecode(re.sub(r'[^\w]+', '', row['artist_credit_name'] + row['recording_name']).lower())
        if combined_lookup not in self.artist_recordings:
            self.artist_recordings[combined_lookup] = (row["artist_credit_id"],
                                                       row["artist_mbids"],
                                                       row["artist_credit_name"],
                                                       row["release_mbid"],
                                                       row["release_name"],
                                                       row["recording_mbid"],
                                                       row["recording_name"],
                                                       combined_lookup,
                                                       row["score"],
                                                       row["year"])
        else:
            other_row = self.artist_recordings[combined_lookup]
            if row["recording_mbid"] != other_row[5]:
                canonical_recording_result.append((row["recording_mbid"],
                                                   other_row[5],
                                                   other_row[3]))

        self.last_artist_credit_id = row['artist_credit_id']

        return {"mapping.mbid_mapping": result,
                "mapping.canonical_recording": canonical_recording_result}

    def process_row_complete(self):
        if self.artist_recordings:
            return {"mapping.mbid_mapping": self.artist_recordings.values()}
        else:
            return None


def create_mbid_mapping():
    """
        Main function for creating the MBID mapping and its related tables.
    """

    with psycopg2.connect(config.MBID_MAPPING_DATABASE_URI) as mb_conn:

        lb_conn = None
        if config.TIMESCALE_DATABASE_URI:
            lb_conn = psycopg2.connect(config.TIMESCALE_DATABASE_URI)

        # Setup all the needed objects
        can = CanonicalRecordings(mb_conn, lb_conn)
        can_rel = CanonicalReleases(mb_conn, lb_conn)
        releases = MBIDMappingReleases(mb_conn)
        mapping = MBIDMapping(mb_conn, lb_conn)
        mapping.add_additional_bulk_table(can)

        # Carry out the bulk of the work
        create_formats_table(mb_conn)
        releases.run(no_swap=True)
        mapping.run(no_swap=True)
        can_rel.run(no_swap=True)

        # Now swap everything into production in a single transaction
        log("mbid_mapping: Swap into production")
        if lb_conn:
            releases.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mapping.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can_rel.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            mb_conn.commit()
            lb_conn.commit()
            lb_conn.close()
        else:
            releases.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mapping.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can_rel.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mb_conn.commit()

        log("mbid_mapping: done done done!")
