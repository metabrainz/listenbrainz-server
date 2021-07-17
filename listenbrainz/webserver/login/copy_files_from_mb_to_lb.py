import psycopg2
from psycopg2.extras import execute_values
from brainzutils.musicbrainz_db.editor import fetch_multiple_editors
from flask import current_app

from listenbrainz import db as lb_db


def copy_emails():
    current_app.logger.info("Beginning to update emails for users...")
    connection = lb_db.engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute('''SELECT musicbrainz_row_id FROM "user"''')
            current_app.logger.info("Fetched editor ids from ListenBrainz.")
            editor_ids = [row[0] for row in cursor.fetchall()]
            editors = fetch_multiple_editors(editor_ids)
            current_app.logger.info("Fetched editor emails from MusicBrainz.")
            emails = [(editor_id, editor['email']) for editor_id, editor in editors.items()]
            query = """
                UPDATE "user"
                SET email = editor_email_temp.email
                FROM (VALUES %s)
                AS editor_email_temp(id, email)
                WHERE editor_email_temp.id = "user".musicbrainz_row_id
            """
            execute_values(cursor, query, emails, template=None)
            current_app.logger.info("Updated emails of ListenBrainz users.")
        connection.commit()
    except psycopg2.errors.OperationalError:
        current_app.logger.error("Error while updating emails of ListenBrainz users", exc_info=True)
        connection.rollback()
    finally:
        connection.close()
