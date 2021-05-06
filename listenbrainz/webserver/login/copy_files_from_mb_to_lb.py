import sqlalchemy

from brainzutils.musicbrainz_db.editor import fetch_multiple_editors
from flask import current_app

from listenbrainz import db as lb_db
from listenbrainz.webserver import create_app


def copy_emails():
    current_app.logger.info("Beginning to update emails for users...")
    with lb_db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""SELECT musicbrainz_row_id FROM "user";"""))
        current_app.logger.info("Fetched editor ids from ListenBrainz.")
        editor_ids = [row['musicbrainz_row_id'] for row in result.fetchall()]
        editors = fetch_multiple_editors(editor_ids)
        current_app.logger.info("Fetched editor emails from MusicBrainz.")
        emails = [(editor_id, editor['email']) for editor_id, editor in editors]
        connection.execute(sqlalchemy.text("""
            UPDATE "user"
            SET email = editor_email_temp.email
            FROM (VALUES :emails) 
            AS editor_email_temp(id, email)
            WHERE editor_email_temp.id = "user".musicbrainz_row_id
        """), {"emails": tuple(emails)})
        current_app.logger.info("Updated emails of ListenBrainz users.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        copy_emails()
