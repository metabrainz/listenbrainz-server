from collections import defaultdict

from flask import current_app
from psycopg2.extras import execute_values, DictCursor
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import timescale


def fixup_table(fetch_query, update_query, unique=False):
    """ Fixup recording_msid duplicates in given table.

        Args:
             fetch_query: the query to retrieve msid rows from the table
             update_query: the query to update the msids for the table
             unique: whether there is a unique index and conflicts need to be removed
    """
    with db.engine.connect() as db_conn, timescale.engine.connect() as ts_conn:
        all_entries = db_conn.execute(fetch_query)

        values = []
        all_users_map = defaultdict(set)
        for row in all_entries:
            values.append((row.id, row.user_id, row.recording_msid))
            all_users_map[row.user_id].add(str(row.recording_msid))

        redirect_query = """
            select row_id, user_id, recording_msid, original_msid
              from (values %s) as t(row_id, user_id, recording_msid)
              join messybrainz.submissions_redirect
                on duplicate_msid = recording_msid::uuid
        """
        ts_curs = ts_conn.connection.cursor(cursor_factory=DictCursor)
        replace_entries = execute_values(ts_curs, redirect_query, values, fetch=True)

        count = 0
        updates = []
        for row in replace_entries:
            # to avoid unique index conflicts if multiple msids redirect to the same original msid
            if unique and str(row["original_msid"]) in all_users_map[row["user_id"]]:
                count += 1
                print(row["row_id"], row["user_id"], str(row["recording_msid"]), str(row["original_msid"]))
                continue
            updates.append((row["row_id"], row["original_msid"]))
            all_users_map[row["user_id"]].add(str(row["original_msid"]))

        if not updates:
            return
        db_curs = db_conn.connection.cursor()
        execute_values(db_curs, update_query, updates)
        db_conn.connection.commit()


def main():
    current_app.logger.info("Fixup recording_feedback table")
    fixup_table(
        text("SELECT id, user_id, recording_msid from recording_feedback"),
        """
            UPDATE recording_feedback
               SET recording_msid = new_msid
              FROM (VALUES %s) AS t(row_id, new_msid)
             WHERE id = row_id
        """
    )

    current_app.logger.info("Fixup pinned_recording table")
    fixup_table(
        text("SELECT id, user_id, recording_msid from pinned_recording"),
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
            SELECT id
                 , user_id
                 , (metadata->>'recording_msid')::UUID AS recording_msid
              FROM user_timeline_event
             WHERE metadata ? 'recording_msid'
        """),
        """
            UPDATE user_timeline_event
               SET metadata = jsonb_set(metadata, '{recording_msid}'::text[], to_jsonb(new_msid::text), true)
              FROM (VALUES %s) AS t(row_id, new_msid)
             WHERE id = row_id
        """
    )
