import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from brainzutils.musicbrainz_db.editor import fetch_multiple_editors
from flask import current_app

from listenbrainz import db as lb_db


def copy_emails():
    current_app.logger.info("Beginning to update emails for users...")
    with lb_db.engine.connect() as connection:
        try:
            result = connection.execute(sqlalchemy.text('''SELECT musicbrainz_row_id FROM "user"'''))
            current_app.logger.info("Fetched editor ids from ListenBrainz.")
            editor_ids = [row['musicbrainz_row_id'] for row in result.fetchall()]
            editors = fetch_multiple_editors(editor_ids)
            current_app.logger.info("Fetched editor emails from MusicBrainz.")
            emails = [(editor_id, editor['email']) for editor_id, editor in editors.items()]
            connection.execute(sqlalchemy.text("""
                UPDATE "user"
                SET email = editor_email_temp.email
                FROM (VALUES :emails) 
                AS editor_email_temp(id, email)
                WHERE editor_email_temp.id = "user".musicbrainz_row_id
            """), {"emails": tuple(emails)})
            current_app.logger.info("Updated emails of ListenBrainz users.")
            connection.commit()
        except SQLAlchemyError as error:
            current_app.logger.error(error, exc_info=True)
            connection.rollback()
