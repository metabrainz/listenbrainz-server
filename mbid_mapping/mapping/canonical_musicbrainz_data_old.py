import re

import psycopg2
from unidecode import unidecode

from mapping.canonical_musicbrainz_data_old_base import CanonicalMusicBrainzDataOldBase
from mapping.canonical_recording_redirect_old import CanonicalRecordingRedirectOld
from mapping.canonical_recording_release_redirect_old import CanonicalRecordingReleaseRedirectOld
from mapping.canonical_release_old import CanonicalReleaseOld
from mapping.canonical_release_redirect_old import CanonicalReleaseRedirectOld
from mapping.utils import log
from mapping.custom_sorts import create_custom_sort_tables

import config


class CanonicalMusicBrainzDataOld(CanonicalMusicBrainzDataOldBase):
    """
        This class creates the MBID mapping tables without release name in the lookup.
    """

    def __init__(self, mb_conn, lb_conn=None, batch_size=None):
        super().__init__("mapping.canonical_musicbrainz_data_old", mb_conn, lb_conn, batch_size)

    def get_post_process_queries(self):
        return ["""
            WITH all_recs AS (
                SELECT *
                     , row_number() OVER (PARTITION BY combined_lookup ORDER BY score) AS rnum
                  FROM mapping.canonical_musicbrainz_data_old_tmp
            ), deleted_recs AS (
                DELETE
                  FROM mapping.canonical_musicbrainz_data_old_tmp
                 WHERE id IN (SELECT id FROM all_recs WHERE rnum > 1)
             RETURNING recording_mbid, combined_lookup
            )
           INSERT INTO mapping.canonical_recording_redirect_old_tmp (recording_mbid, canonical_recording_mbid, canonical_release_mbid)
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
            # (f"{table}_idx_artist_credit_recording_name", "artist_credit_name, recording_name", False),
            (f"{table}_idx_recording_mbid", "recording_mbid", True)
        ]


def create_canonical_musicbrainz_data_old(use_lb_conn: bool):
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
        can = CanonicalRecordingRedirectOld(mb_conn, lb_conn)
        can_rec_rel = CanonicalRecordingReleaseRedirectOld(mb_conn, lb_conn)
        can_rel = CanonicalReleaseRedirectOld(mb_conn)
        releases = CanonicalReleaseOld(mb_conn)
        mapping = CanonicalMusicBrainzDataOld(mb_conn, lb_conn)
        mapping.add_additional_bulk_table(can)

        # # Carry out the bulk of the work
        # create_custom_sort_tables(mb_conn)
        # releases.run(no_swap=True)
        # mapping.run(no_swap=True)
        # can_rec_rel.run(no_swap=True)
        # can_rel.run(no_swap=True)

        # Now swap everything into production in a single transaction
        log("canonical_musicbrainz_data: Swap into production")
        if lb_conn:
            releases.swap_into_production(no_swap_transaction=True, swap_conn=mb_conn)
            mapping.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can_rec_rel.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
            can_rel.swap_into_production(no_swap_transaction=True, swap_conn=lb_conn)
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

"""
select cmd.combined_lookup
     , cmd.recording_name
     , cmd.artist_credit_name
     , cmd.recording_mbid
     , cmdo.recording_mbid
     , cmd.release_mbid
     , cmdo.release_mbid
  from mapping.canonical_musicbrainz_data_old cmdo
  join mapping.canonical_musicbrainz_data cmd
    on cmdo.combined_lookup = cmd.combined_lookup
   and cmdo.recording_mbid != cmd.recording_mbid
   and cmdo.release_mbid != cmd.release_mbid
   and cmdo.artist_credit_id != 1
   and cmd.artist_credit_id != 1
  join musicbrainz.release r
    on r.gid = cmdo.release_mbid
  join musicbrainz.release_group rg
    on rg.id = r.release_group
  join musicbrainz.release_group_secondary_type_join rgstj
    on rgstj.release_group = rg.id
   and rgstj.secondary_type = 2;
"""
