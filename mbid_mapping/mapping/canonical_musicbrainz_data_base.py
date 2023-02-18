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
