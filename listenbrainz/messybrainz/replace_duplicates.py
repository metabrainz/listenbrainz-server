from flask import current_app
from psycopg2.extras import execute_values
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import timescale


def fixup_table(fetch_query, update_query):
    """ Fixup recording_msid duplicates in given table.

        Args:
             fetch_query: the query to retrieve msid rows from the table
             update_query: the query to update the msids for the table
    """
    with db.engine.connect() as db_conn, timescale.engine.connect() as ts_conn:
        all_entries = db_conn.execute(fetch_query)
        all_entries_map = {row.recording_msid: row.id for row in all_entries}

        redirect_query = """
            select msid, original_msid
              from (values %s) as t(msid)
              join messybrainz.submissions_redirect
                on duplicate_msid = msid
        """
        ts_curs = ts_conn.connection.cursor()
        replace_entries = execute_values(ts_curs, redirect_query, [(msid,) for msid in all_entries_map.keys()], fetch=True)

        updates = []
        for row in replace_entries:
            row_id = all_entries_map[row[0]]
            updates.append((row_id, row[1]))

        db_curs = db_conn.connection.cursor()
        execute_values(db_curs, update_query, updates)
        db_conn.connection.commit()


def main():
    current_app.logger.info("Fixup recording_feedback table")
    fixup_table(
        text("select id, recording_msid from recording_feedback"),
        """
            UPDATE recording_feedback
               SET recording_msid = new_msid
              FROM (VALUES %s) AS t(row_id, new_msid)
             WHERE id = row_id
        """
    )

    current_app.logger.info("Fixup pinned_recording table")
    fixup_table(
        text("select id, recording_msid from pinned_recording"),
        """
            UPDATE pinned_recording
               SET recording_msid = new_msid
              FROM (VALUES %s) AS t(row_id, new_msid)
             WHERE id = row_id
        """
    )

    current_app.logger.info("Fixup user_timeline_event table")
    fixup_table(
        text("""
            select id
                 , (metadata->>'recording_msid')::UUID AS recording_msid
              FROM user_timeline_event
             WHERE metadata ? 'recording_msid'
        """),
        """
            UPDATE user_timeline_event
               SET metadata = jsonb_set(metadata, '{{recording_msid}}'::text[], to_jsonb(new_msid::text), true)
              FROM (VALUES %s) AS t(row_id, new_msid)
             WHERE id = row_id
        """
    )
