import sqlalchemy

from listenbrainz import db
from listenbrainz.db.model.feedback import Feedback


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
    """ Deletes the feedback record for a given recording for the user from the database

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


def get_feedback_for_user(user_id: int, limit: int, offset: int, score: int = None):
    """ Get a list of recording feedback given by the user in descending order of their creation

        Args:
            user_id: the row ID of the user in the DB
            score: the score value by which the results are to be filtered. If 1 then returns the loved recordings,
                   if -1 returns hated recordings.
            limit: number of rows to be returned
            offset: number of feedback to skip from the beginning

        Returns:
            A list of Feedback objects
    """

    args = {"user_id": user_id, "limit": limit, "offset": offset}
    query = """ SELECT user_id, "user".musicbrainz_id AS user_name, recording_msid::text, score
                  FROM recording_feedback
                 JOIN "user"
                  ON "user".id = recording_feedback.user_id
                 WHERE user_id = :user_id """

    if score:
        query += "AND score = :score"
        args["score"] = score

    query += """ ORDER BY recording_feedback.created DESC
                 LIMIT :limit OFFSET :offset """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        return [Feedback(**dict(row)) for row in result.fetchall()]


def get_feedback_count_for_user(user_id: int):
    """ Get total number of recording feedback given by the user

        Args:
            user_id: the row ID of the user in the DB

        Returns:
            The total number of recording feedback given by the user
    """

    query = "SELECT count(*) AS value FROM recording_feedback WHERE user_id = :user_id"

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), {
                'user_id': user_id,
            }
        )
        count = int(result.fetchone()["value"])

    return count


def get_feedback_for_recording(recording_msid: str, limit: int, offset: int, score: int = None):
    """ Get a list of recording feedback for a given recording in descending order of their creation

        Args:
            recording_msid: the MessyBrainz ID of the recording
            score: the score value by which the results are to be filtered. If 1 then returns the loved recordings,
                   if -1 returns hated recordings.
            limit: number of rows to be returned
            offset: number of feedback to skip from the beginning

        Returns:
            A list of Feedback objects
    """

    args = {"recording_msid": recording_msid, "limit": limit, "offset": offset}
    query = """ SELECT user_id, "user".musicbrainz_id AS user_name, recording_msid::text, score
                  FROM recording_feedback
                 JOIN "user"
                  ON "user".id = recording_feedback.user_id
                 WHERE recording_msid = :recording_msid """

    if score:
        query += "AND score = :score"
        args["score"] = score

    query += """ ORDER BY recording_feedback.created DESC
                 LIMIT :limit OFFSET :offset """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        return [Feedback(**dict(row)) for row in result.fetchall()]


def get_feedback_count_for_recording(recording_msid: str):
    """ Get total number of recording feedback for a given recording

        Args:
            recording_msid: the MessyBrainz ID of the recording

        Returns:
            The total number of recording feedback for a given recording
    """

    query = "SELECT count(*) AS value FROM recording_feedback WHERE recording_msid = :recording_msid"

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), {
                'recording_msid': recording_msid,
            }
        )
        count = int(result.fetchone()["value"])

    return count
