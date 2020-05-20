import sqlalchemy

from listenbrainz import db


def insert(user_id, recording_msid, score):
    """ Inserts a feedback record for a user's loved/hated recording into the database.
        If the record is already present for the user, the score is updated to the new
        value passed.
        Args:
            user_id (int): the row id of the user
            recording_msid (string): the MessyBrainz ID of the recording
            score (int): The score associated with the recording (+1/-1 for love/hate respectively)
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO recording_feedback (user_id, recording_msid, score)
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


def delete(user_id, recording_msid):
    """ Deletes the feedback record for a given recording for the user from the database.
        Args:
            user_id (int): the row id of the user
            recording_msid (dict): the MessyBrainz ID of the recording
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM recording_feedback
             WHERE user_id = :user_id
               AND recording_msid = :recording_msid
            """), {
                'user_id': user_id,
                'recording_msid': recording_msid,
            }
        )


def get_feedback(user_id):
    """ Get a list of recording feedbacks given by the user.
        Args:
            user_id (int): the row ID of the user in the DB
        Returns:
            A list of user's loved and hated recordings
    """
    records = []
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, recording_msid, score
              FROM recording_feedback
          ORDER BY created DESC
            """), {
                'user_id': user_id
            }
        )
        while True:
            row = result.fetchone()
            if not row:
                break

            records.append(_format_recording_feedback_row(row[0], row[1], row[2]))

    return records


def get_feedback_single_type(user_id, score):
    """ Get a list of recording feedbacks of particular type (loved or hated) given by the user.
        If score is +1 then get loved recordings, if -1 then get hated recordings.
        Args:
            user_id (int): the row ID of the user
        Returns:
            A list of user's loved or hated recordings
    """

    records = []
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, recording_msid, score
              FROM recording_feedback
             WHERE user_id = :user_id
               AND score = :score
          ORDER BY created DESC
            """), {
                'user_id': user_id,
                'score': score
            }
        )
        while True:
            row = result.fetchone()
            if not row:
                break

            records.append(_format_recording_feedback_row(row[0], row[1], row[2]))

    return records


def get_feedback_for_recording(recording_msid):
    """ Get a list of feedbacks for a given recording.
        Args:
            recording_msid (string): the MessyBrainz ID of the recording
        Returns:
            A list of feedbacks for the given recording
    """

    records = []
    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT user_id, recording_msid, score
              FROM recording_feedback
             WHERE recording_msid = :recording_msid
          ORDER BY created DESC
            """), {
                'recording_msid': recording_msid
            }
        )
        while True:
            row = result.fetchone()
            if not row:
                break

            records.append(_format_recording_feedback_row(row[0], row[1], row[2]))

    return records


def _format_recording_feedback_row(user_id, recording_msid, score):
    """ Format the given entires into a dict.
        Args:
            user_id (int): the row id of the user
            recording_msid (string): the MessyBrainz ID of the recording
            score (int): The score associated with the recording
        Returns:
            A dict formed from the args.
    """
    record = {
        'user_id': user_id,
        'recording_msid': recording_msid,
        'score': score,
    }
    return record
