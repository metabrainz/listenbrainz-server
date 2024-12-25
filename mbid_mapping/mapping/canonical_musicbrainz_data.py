import re

import psycopg2
from unidecode import unidecode

from mapping.canonical_musicbrainz_data_base import CanonicalMusicBrainzDataBase
from mapping.canonical_musicbrainz_data_release_support import CanonicalMusicBrainzDataReleaseSupport
from mapping.utils import log
from mapping.custom_sorts import create_custom_sort_tables
from mapping.canonical_recording_redirect import CanonicalRecordingRedirect
from mapping.canonical_recording_release_redirect import CanonicalRecordingReleaseRedirect
from mapping.canonical_release_redirect import CanonicalReleaseRedirect
from mapping.canonical_release import CanonicalRelease

import config


class CanonicalMusicBrainzData(CanonicalMusicBrainzDataBase):
    """
        This class creates the MBID mapping tables without release name in the lookup.
    """

    def __init__(self, select_conn, insert_conn=None, batch_size=None, unlogged=False):
        super().__init__("mapping.canonical_musicbrainz_data", select_conn, insert_conn, batch_size, unlogged)

    def get_post_process_queries(self):
        return ["""
            WITH all_recs AS (
                SELECT *
                     , row_number() OVER (PARTITION BY combined_lookup ORDER BY score) AS rnum
                  FROM mapping.canonical_musicbrainz_data_tmp
            ), deleted_recs AS (
                DELETE
                  FROM mapping.canonical_musicbrainz_data_tmp
                 WHERE id IN (SELECT id FROM all_recs WHERE rnum > 1)
             RETURNING recording_mbid, combined_lookup
            )
           INSERT INTO mapping.canonical_recording_redirect_tmp (recording_mbid, canonical_recording_mbid, canonical_release_mbid)
                SELECT t1.recording_mbid
                     , t2.recording_mbid AS canonical_recording
                     , t2.release_mbid AS canonical_release
                  FROM deleted_recs t1
                  JOIN all_recs t2
                    ON t1.combined_lookup = t2.combined_lookup
                 WHERE t2.rnum = 1
                 -- some recording mbids appear on multiple releases and the insert query inserts them once for
                 -- for each appearance with the appropriate release mbid. the deletion criteria is combined_lookup
                 -- which is unavailable in the insert sql query so we cannot easily apply a filter there itself.
                 -- such rows cleaned up in the deleted_recs with above so to above adding a redirect to the same
                 -- recording as a canonical_recording, this condition.
                   AND t1.recording_mbid != t2.recording_mbid;
        """]

    def get_combined_lookup(self, row):
        return unidecode(re.sub(r'[^\w]+', '', row['artist_credit_name'] + row['recording_name']).lower())

    def get_index_names(self):
        table = self.table_name.split(".")[-1]
        return [
            (f"{table}_idx_combined_lookup",              "combined_lookup", False),
            (f"{table}_idx_artist_credit_recording_name", "artist_credit_name, recording_name", False),
            (f"{table}_idx_recording_mbid", "recording_mbid", True)
        ]


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
            unlogged = False
        else:
            unlogged = True

        # Setup all the needed objects
        releases = CanonicalRelease(mb_conn, unlogged=False)
        can = CanonicalRecordingRedirect(mb_conn, lb_conn, unlogged=unlogged)
        mapping = CanonicalMusicBrainzData(mb_conn, lb_conn, unlogged=unlogged)
        mapping.add_additional_bulk_table(can)
        can_rel = CanonicalReleaseRedirect(mb_conn, lb_conn, unlogged=unlogged)

        if lb_conn:
            can_rec_rel = CanonicalRecordingReleaseRedirect(lb_conn, mb_conn, unlogged=unlogged)
        else:
            can_rec_rel = CanonicalRecordingReleaseRedirect(mb_conn, unlogged=unlogged)

        mapping_release = CanonicalMusicBrainzDataReleaseSupport(mb_conn, lb_conn, unlogged=unlogged)

        # Carry out the bulk of the work
        create_custom_sort_tables(mb_conn)
        releases.run(no_swap=True)
        mapping.run(no_swap=True)
        can_rel.run(no_swap=True)

        can_rec_rel.run(no_swap=True)
        mapping_release.run(no_swap=True)

        # Now swap everything into production in a single transaction
        log("canonical_musicbrainz_data: Swap into production")
        if lb_conn:
            releases.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mapping_release.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            mapping.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can_rec_rel.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can_rel.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            mb_conn.commit()
            lb_conn.commit()
            lb_conn.close()
        else:
            releases.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mapping_release.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mapping.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can_rec_rel.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            can_rel.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mb_conn.commit()

        log("canonical_musicbrainz_data: done done done!")


def update_canonical_release_data(use_lb_conn: bool):
    """
        Run only the canonical release data, apart from the other tables.

        Arguments:
            use_lb_conn: whether to use LB conn or not
    """
    mb_uri = config.MB_DATABASE_MASTER_URI or config.MBID_MAPPING_DATABASE_URI

    with psycopg2.connect(mb_uri) as mb_conn:

        lb_conn = None
        if use_lb_conn and config.SQLALCHEMY_TIMESCALE_URI:
            lb_conn = psycopg2.connect(config.SQLALCHEMY_TIMESCALE_URI)
            releases = CanonicalRelease(mb_conn, lb_conn, unlogged=False)
        else:
            releases = CanonicalRelease(mb_conn, unlogged=False)
        releases.run()

        log("canonical_release_data: updated.")
