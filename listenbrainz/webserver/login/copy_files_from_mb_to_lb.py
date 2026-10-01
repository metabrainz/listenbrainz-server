import psycopg2
from psycopg2.extras import execute_values
from flask import current_app

from listenbrainz import db as lb_db
from listenbrainz.db import donation

EMAIL_BATCH_SIZE = 10_000


def copy_emails(batch_size: int = EMAIL_BATCH_SIZE) -> int:
    """Backfill missing ListenBrainz emails from confirmed MetaBrainz accounts."""
    if donation.engine is None:
        raise RuntimeError("MetaBrainz database connection is not configured")
    if batch_size <= 0:
        raise ValueError("Email batch size must be positive")

    current_app.logger.info("Beginning to update emails for users...")
    lb_connection = None
    meb_connection = None
    updated = 0
    last_lb_user_id = 0

    try:
        lb_connection = lb_db.engine.raw_connection()
        meb_connection = donation.engine.raw_connection()
        with lb_connection.cursor() as lb_cursor, meb_connection.cursor() as meb_cursor:
            while True:
                lb_cursor.execute(
                    """
                    SELECT id, musicbrainz_row_id
                      FROM "user"
                     WHERE id > %s
                       AND musicbrainz_row_id IS NOT NULL
                       AND email IS NULL
                  ORDER BY id
                     LIMIT %s
                    """,
                    (last_lb_user_id, batch_size),
                )
                lb_users = lb_cursor.fetchall()
                if not lb_users:
                    break

                last_lb_user_id = lb_users[-1][0]
                meb_user_ids = [row[1] for row in lb_users]
                meb_cursor.execute(
                    """
                    SELECT id, email
                      FROM "user"
                     WHERE id = ANY(%s)
                       AND email IS NOT NULL
                    """,
                    (meb_user_ids,),
                )
                emails = meb_cursor.fetchall()
                if not emails:
                    continue

                updated_rows = execute_values(
                    lb_cursor,
                    """
                    UPDATE "user" AS lb_user
                       SET email = meb_user.email
                      FROM (VALUES %s) AS meb_user(id, email)
                     WHERE lb_user.musicbrainz_row_id = meb_user.id
                       AND lb_user.email IS NULL
                 RETURNING lb_user.id
                    """,
                    emails,
                    template=None,
                    fetch=True,
                )
                lb_connection.commit()
                updated += len(updated_rows)

        current_app.logger.info("Updated emails of %d ListenBrainz users.", updated)
        return updated
    except psycopg2.Error:
        current_app.logger.error("Error while updating emails of ListenBrainz users", exc_info=True)
        if lb_connection is not None:
            lb_connection.rollback()
        raise
    finally:
        if meb_connection is not None:
            meb_connection.close()
        if lb_connection is not None:
            lb_connection.close()
