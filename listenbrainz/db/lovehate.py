import sqlalchemy

from listenbrainz import db


def insert_lovehate_record(user_id, recording_msid, score):
    """ Inserts a record for a user's loved/hated recording into the database.
        If the record is already present for the user, the score is updated to the new
        value passed.
        Args:
            user_id (int): the row id of the user
            recording_msid (string): the MessyBrainz ID of the recording
            score (int): The score associated with the recording (+1/-1 for love/hate respectively)
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO recording_lovehate (user_id, recording_msid, score)
                 VALUES (:user_id, :recording_msid, :score)
            ON CONFLICT (user_id, recording_msid)
          DO UPDATE SET score = :score,
                        created = NOW()
            """), {
                'user_id': user_id,
                'recording_msid': recording_msid,
                'score': score,
            }
        )


def delete_lovehate_record(user_id, recording_msid):
    """ Deletes the record for a user's loved/hated recording from the database.
        Args:
            user_id (int): the row id of the user
            recording_msid (dict): the MessyBrainz ID of the recording
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM recording_lovehate
             WHERE user_id = :user_id
               AND recording_msid = :recording_msid
            """), {
                'user_id': user_id,
                'recording_msid': recording_msid,
            }
        )


def get_user_loved_or_hated_recordings(user_id, score):
    """ Get a particular user's loved or hated recordings. If score is +1 then
        get loved recordings, if -1 then get hated recordings.
        Args:
            user_id (int): the row ID of the user
        Returns:
            A list of user's loved or hated recordings
    """

    records = []
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, recording_msid, score
              FROM recording_lovehate
             WHERE user_id = :user_id
               AND score = :score
            """), {
                'score': score
            }
        )
        while True:
            row = result.fetchone()
            if not row:
                return None

            records.append(_format_recording_lovehate_row(row[0], row[1], row[2]))
        return records


def get_user_loved_and_hated_recordings(user_id):
    """ Get a particular user's loved and hated recordings.
        Args:
            user_id (int): the row ID of the user in the DB
        Returns:
            A list of user's loved and hated recordings
    """
    records = []
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, recording_msid, score
              FROM recording_lovehate
             WHERE user_id = :user_id
            """), {
                'user_id': user_id
            }
        )
        while True:
            row = result.fetchone()
            if not row:
                return None

            records.append(_format_recording_lovehate_row(row[0], row[1], row[2]))
        return records


def get_records_for_given_recording(recording_msid):
    """ Get all records associated with a given recording.
        Args:
            recording_msid (string): the MessyBrainz ID of the recording
        Returns:
            A list of records for the given recording
    """

    records = []
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, recording_msid, score
              FROM recording_lovehate
             WHERE recording_msid = :recording_msid
            """), {
                'user_id': user_id
            }
        )
        while True:
            row = result.fetchone()
            if not row:
                return None

            records.append(_format_recording_lovehate_row(row[0], row[1], row[2]))
        return records


def _format_recording_lovehate_row(user_id, recording_msid, score):
    record = {
        'user_id': user_id,
        'recording_msid': recording_msid,
        'score': self.score,
    }
    return record
