from sqlalchemy import text

from listenbrainz import db


def insert_recording_discovery(data):
    with db.engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO statistics.recording_discovery (user_id, recording_mbid, first_listened_at, latest_listened_at)
                 SELECT "user".id
                      , recording_mbid
                      , first_listened_at
                      , latest_listened_at
                   FROM json_populate_recordset(null::statistics.recording_discovery, :data)
                   JOIN "user" ON "user".id = user_id -- to remove rows for users that do not exist
        """), data=data)
