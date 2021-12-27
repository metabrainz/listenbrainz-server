import sqlalchemy
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.db.mapping import fetch_track_metadata_for_items
from listenbrainz.db.model.feedback import Feedback
from listenbrainz import messybrainz as msb_db
from listenbrainz.messybrainz.data import load_recordings_from_msids
from typing import List
from listenbrainz.messybrainz.exceptions import NoDataFoundException


def insert(feedback: Feedback):
    """ Inserts a feedback record for a user's loved/hated recording into the database.
        If the record is already present for the user, the score is updated to the new
        value passed.

        Args:
            feedback: An object of class Feedback
    """

    with db.engine.connect() as connection:
        connection.execute(sqlalchemy.text("""
            INSERT INTO recording_feedback (user_id, recording_msid, recording_mbid, score)
                 VALUES (:user_id, :recording_msid, :recording_mbid, :score)
            ON CONFLICT (user_id, recording_mbid)
          DO UPDATE SET score = :score
                      , recording_msid = :recording_msid
                      , created = NOW()
            """), {
            'user_id': feedback.user_id,
            'recording_msid': feedback.recording_msid,
            'recording_mbid': feedback.recording_mbid,
            'score': feedback.score,
        })


def delete(feedback: Feedback):
    """ Deletes the feedback record for a given recording for the user from the database

        Args:
            feedback: An object of class Feedback
    """
    conditions = [text("user_id = :user_id")]
    args = {"user_id": feedback.user_id}

    if feedback.recording_msid:
        conditions.append("recording_msid = :recording_msid")
        args["recording_msid"] = feedback.recording_msid

    if feedback.recording_mbid:
        conditions.append("recording_mbid = :recording_mbid")
        args["recording_mbid"] = feedback.recording_mbid

    where_clause = " AND ".join(conditions)

    with db.engine.connect() as connection:
        connection.execute(text("DELETE FROM recording_feedback WHERE ") + where_clause, args)


def get_feedback_for_user(user_id: int, limit: int, offset: int, score: int = None, metadata: bool = False) -> List[Feedback]:
    """ Get a list of recording feedback given by the user in descending order of their creation

        Args:
            user_id: the row ID of the user in the DB
            score: the score value by which the results are to be filtered. If 1 then returns the loved recordings,
                   if -1 returns hated recordings.
            limit: number of rows to be returned
            offset: number of feedback to skip from the beginning
            metadata: fetch metadata for the returned feedback recordings

        Returns:
            A list of Feedback objects
    """

    args = {"user_id": user_id, "limit": limit, "offset": offset}
    query = """ SELECT user_id
                     , "user".musicbrainz_id AS user_name
                     , recording_msid::text
                     , recording_mbid::text
                     , score
                     , recording_feedback.created
                  FROM recording_feedback
                  JOIN "user"
                    ON "user".id = recording_feedback.user_id
                 WHERE user_id = :user_id
    """

    if score:
        query += " AND score = :score"
        args["score"] = score

    query += """ ORDER BY recording_feedback.created DESC
                 LIMIT :limit OFFSET :offset """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        feedback = [Feedback(**dict(row)) for row in result.fetchall()]

    if metadata and len(feedback) > 0:
        feedback = fetch_track_metadata_for_items(feedback)

    return feedback


def get_feedback_count_for_user(user_id: int, score=None) -> int:
    """ Get total number of recording feedback given by the user

        Args:
            user_id: the row ID of the user in the DB
            score: If 1, fetch count for all the loved feedback,
                   if -1 fetch count for all the hated feedback,
                   if None, fetch count for all feedback

        Returns:
            The total number of recording feedback given by the user
    """

    query = "SELECT count(*) AS value FROM recording_feedback WHERE user_id = :user_id"
    args = {'user_id': user_id}

    if score is not None:
        query += " AND score = :score"
        args['score'] = score

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        count = int(result.fetchone()["value"])

    return count


def get_feedback_for_recording(recording: str, limit: int, offset: int, score: int = None) -> List[Feedback]:
    """ Get a list of recording feedback for a given recording in descending order of their creation

        Args:
            recording: the msid or mbid of the recording
            score: the score value by which the results are to be filtered. If 1 then returns the loved recordings,
                   if -1 returns hated recordings.
            limit: number of rows to be returned
            offset: number of feedback to skip from the beginning

        Returns:
            A list of Feedback objects
    """

    args = {"recording": recording, "limit": limit, "offset": offset}
    query = """ SELECT user_id
                     , "user".musicbrainz_id AS user_name
                     , recording_msid::text
                     , recording_mbid::text
                     , score
                     , recording_feedback.created
                  FROM recording_feedback
                  JOIN "user"
                    ON "user".id = recording_feedback.user_id
                 WHERE recording_msid = :recording
                    OR recording_mbid = :recording
    """

    if score:
        query += " AND score = :score"
        args["score"] = score

    query += """ ORDER BY recording_feedback.created DESC
                 LIMIT :limit OFFSET :offset """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        return [Feedback(**dict(row)) for row in result.fetchall()]


def get_feedback_count_for_recording(recording_msid: str) -> int:
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


def get_feedback_for_multiple_recordings_for_user(user_id: int, user_name: str, recording_msids: List[str],
                                                  recording_mbids: List[str]) -> List[Feedback]:
    """ Get a list of recording feedback given by the user for given recordings

        For each recording msid and recording mbid,
            - if record is present then return it
            - if record is not present then return a pseudo record with score = 0

        Args:
            user_id: the row ID of the user in the DB
            user_name: the user name of the user, not used in the query but only for creating the
                response to be returned from the api
            recording_msids: list of recording_msid for which feedback records are to be obtained
            recording_mbids: list of recording_mbid for which feedback records are to be obtained

        Returns:
            A list of Feedback objects
    """
    query = """
            WITH rf AS (
              SELECT user_id, recording_msid::text, recording_mbid::text, score
                FROM recording_feedback
               WHERE recording_feedback.user_id = :user_id
            )
              SELECT recording_msid
                   , recording_mbid
                   , COALESCE(rf.score, 0) AS score
                FROM UNNEST(:recording_msids) recording_msid
     LEFT OUTER JOIN rf
               USING (recording_msid)
           UNION ALL
              SELECT recording_msid
                   , recording_mbid
                   , COALESCE(rf.score, 0) AS score
                FROM UNNEST(:recording_mbids) recording_mbid
     LEFT OUTER JOIN rf
               USING (recording_mbid)
    """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), user_id=user_id,
                                    recording_msids=recording_msids, recording_mbids=recording_mbids)
        return [Feedback(user_id=user_id, user_name=user_name, **dict(row)) for row in result.fetchall()]
