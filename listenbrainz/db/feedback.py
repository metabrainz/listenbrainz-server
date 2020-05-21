import sqlalchemy

from listenbrainz import db
from listenbrainz.feedback import Feedback


def insert(feedback: Feedback):
    """ Inserts a feedback record for a user's loved/hated recording into the database.
        If the record is already present for the user, the score is updated to the new
        value passed.
        Args:
            feedback: An object of class Feedback
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO recording_feedback (user_id, recording_msid, score)
                 VALUES (:user_id, :recording_msid, :score)
            ON CONFLICT (user_id, recording_msid)
          DO UPDATE SET score = :score,
                        created = NOW()
            """), {
                'user_id': feedback.user_id,
                'recording_msid': feedback.recording_msid,
                'score': feedback.score,
            }
        )


def delete(feedback: Feedback):
    """ Deletes the feedback record for a given recording for the user from the database.
        Args:
            feedback: An object of class Feedback
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM recording_feedback
             WHERE user_id = :user_id
               AND recording_msid = :recording_msid
            """), {
                'user_id': feedback.user_id,
                'recording_msid': feedback.recording_msid,
            }
        )


def get_feedback_by_user_id(user_id: int):
    """ Get a list of recording feedbacks given by the user.
        Args:
            user_id: the row ID of the user in the DB
        Returns:
            A list of user's feedback
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
        return [Feedback(user_id=row["user_id"], recording_msid=str(row["recording_msid"]), score=row["score"])
                for row in result.fetchall() if row['user_id'] is not None]


def get_feedback_by_user__id_and_score(user_id: int, score: int):
    """ Get a list of recording feedbacks of particular type (loved or hated) given by the user.
        If score is +1 then get loved recordings, if -1 then get hated recordings.
        Args:
            user_id: the row ID of the user
        Returns:
            A list of user's feedback
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
        return [Feedback(user_id=row["user_id"], recording_msid=str(row["recording_msid"]), score=row["score"])
                for row in result.fetchall() if row['user_id'] is not None]


def get_feedback_by_recording_msid(recording_msid: str):
    """ Get a list of feedbacks for a given recording.
        Args:
            recording_msid: the MessyBrainz ID of the recording
        Returns:
            A list of recording feedback
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
        return [Feedback(user_id=row["user_id"], recording_msid=str(row["recording_msid"]), score=row["score"])
                for row in result.fetchall() if row['user_id'] is not None]
