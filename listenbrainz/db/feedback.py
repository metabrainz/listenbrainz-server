import sqlalchemy
from sqlalchemy import text

from listenbrainz import db
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.db.model.feedback import Feedback
from typing import List

INSERT_QUERIES = {
    "msid": """
        INSERT INTO recording_feedback (user_id, recording_msid, score)
             VALUES (:user_id, :recording_msid, :score)
    """,
    "mbid": """
        INSERT INTO recording_feedback (user_id, recording_mbid, score)
             VALUES (:user_id, :recording_mbid, :score)
    """,
    "both": """
        INSERT INTO recording_feedback (user_id, recording_mbid, recording_msid, score)
             VALUES (:user_id, :recording_mbid, :recording_msid, :score)
    """
}

DELETE_QUERIES = {
    "msid": "DELETE FROM recording_feedback WHERE user_id = :user_id AND recording_msid = :recording_msid",
    "mbid": "DELETE FROM recording_feedback WHERE user_id = :user_id AND recording_mbid = :recording_mbid",
    "both": """
        DELETE FROM recording_feedback
              WHERE user_id = :user_id
                AND (
                    recording_msid = :recording_msid
                 OR recording_mbid = :recording_mbid
                    )
    """
}


def insert(db_conn, feedback: Feedback):
    """ Inserts a feedback record for a user's loved/hated recording into the database.
        If the record is already present for the user, the score is updated to the new
        value passed.

        Args:
            db_conn: database connection
            feedback: An object of class Feedback
    """

    params = {
        'user_id': feedback.user_id,
        'score': feedback.score,
    }

    if feedback.recording_msid is not None and feedback.recording_mbid is not None:
        # both recording_msid and recording_mbid available
        params['recording_msid'] = feedback.recording_msid
        params['recording_mbid'] = feedback.recording_mbid
        delete_query = DELETE_QUERIES["both"]
        insert_query = INSERT_QUERIES["both"]
    elif feedback.recording_mbid is not None:  # only recording_mbid available
        params['recording_mbid'] = feedback.recording_mbid
        delete_query = DELETE_QUERIES["mbid"]
        insert_query = INSERT_QUERIES["mbid"]
    else:  # only recording_msid available
        params['recording_msid'] = feedback.recording_msid
        delete_query = DELETE_QUERIES["msid"]
        insert_query = INSERT_QUERIES["msid"]

    # delete the existing feedback and then insert new feedback. we cannot use ON CONFLICT DO UPDATE
    # because it is possible for a user to submit the feedback using recording_msid only and then using
    # both recording_msid and recording_mbid at once in which case the ON CONFLICT doesn't work well.
    db_conn.execute(text(delete_query), params)
    db_conn.execute(text(insert_query), params)
    db_conn.commit()


def delete(db_conn, feedback: Feedback):
    """ Deletes the feedback record for a given recording for the user from the database

        Args:
            db_conn: database connection
            feedback: An object of class Feedback
    """
    params = {"user_id": feedback.user_id}

    if feedback.recording_msid is not None and feedback.recording_mbid is not None:
        # both recording_msid and recording_mbid available
        params['recording_msid'] = feedback.recording_msid
        params['recording_mbid'] = feedback.recording_mbid
        query = DELETE_QUERIES["both"]
    elif feedback.recording_mbid is not None:  # only recording_mbid available
        params['recording_mbid'] = feedback.recording_mbid
        query = DELETE_QUERIES["mbid"]
    else:  # only recording_msid available
        params['recording_msid'] = feedback.recording_msid
        query = DELETE_QUERIES["msid"]

    db_conn.execute(text(query), params)
    db_conn.commit()


def get_feedback_for_user(db_conn, ts_conn, user_id: int, limit: int, offset: int,
                          score: int = None, metadata: bool = False) -> List[Feedback]:
    """ Get a list of recording feedback given by the user in descending order of their creation

        Args:
            db_conn: database connection
            ts_conn: timescale database connection
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

    result = db_conn.execute(sqlalchemy.text(query), args)
    feedback = [Feedback(**row) for row in result.mappings()]

    if metadata and len(feedback) > 0:
        feedback = fetch_track_metadata_for_items(ts_conn, feedback)

    return feedback


def get_feedback_count_for_user(db_conn, user_id: int, score=None) -> int:
    """ Get total number of recording feedback given by the user

        Args:
            db_conn: database connection
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

    result = db_conn.execute(text(query), args)
    count = int(result.fetchone().value)

    return count


def get_feedback_for_recording(db_conn, recording_type: str, recording: str, limit: int,
                               offset: int, score: int = None) -> List[Feedback]:
    """ Get a list of recording feedback for a given recording in descending order of their creation

        Args:
            db_conn: database connection
            recording_type: type of id, recording_msid or recording_mbid
            recording: the msid or mbid of the recording
            score: the score value by which the results are to be filtered. If 1 then returns the loved recordings,
                   if -1 returns hated recordings.
            limit: number of rows to be returned
            offset: number of feedback to skip from the beginning

        Returns:
            A list of Feedback objects
    """

    args = {"recording": recording, "limit": limit, "offset": offset}
    query = """
        SELECT user_id
             , "user".musicbrainz_id AS user_name
             , recording_msid::text
             , recording_mbid::text
             , score
             , recording_feedback.created
          FROM recording_feedback
          JOIN "user"
            ON "user".id = recording_feedback.user_id
         WHERE """ + recording_type + " = :recording"

    if score:
        query += " AND score = :score"
        args["score"] = score

    query += """ ORDER BY recording_feedback.created DESC
                 LIMIT :limit OFFSET :offset """

    result = db_conn.execute(text(query), args)
    return [Feedback(**row) for row in result.mappings()]


def get_feedback_count_for_recording(db_conn, recording_type: str, recording: str) -> int:
    """ Get total number of recording feedback for a given recording

        Args:
            db_conn: database connection
            recording_type: type of id, recording_msid or recording_mbid
            recording: the ID of the recording

        Returns:
            The total number of recording feedback for a given recording
    """
    query = "SELECT count(*) AS value FROM recording_feedback WHERE " + recording_type + " = :recording"
    result = db_conn.execute(text(query), {"recording": recording})
    count = int(result.fetchone().value)
    return count


def get_feedback_for_multiple_recordings_for_user(db_conn, user_id: int, user_name: str, recording_msids: List[str],
                                                  recording_mbids: List[str]) -> List[Feedback]:
    """ Get a list of recording feedback given by the user for given recordings

        For each recording msid and recording mbid,
            - if record is present then return it
            - if record is not present then return a pseudo record with score = 0

        Args:
            db_conn: database connection
            user_id: the row ID of the user in the DB
            user_name: the user name of the user, not used in the query but only for creating the
                response to be returned from the api
            recording_msids: list of recording_msid for which feedback records are to be obtained
            recording_mbids: list of recording_mbid for which feedback records are to be obtained

        Returns:
            A list of Feedback objects
    """
    params = {
        "user_id": user_id
    }

    query_base = """
            WITH rf AS (
              SELECT user_id, recording_msid::text, recording_mbid::text, score
                FROM recording_feedback
               WHERE recording_feedback.user_id = :user_id
            )
    """

    query_msid = """
              SELECT recording_msid
                   , recording_mbid
                   , COALESCE(rf.score, 0) AS score
                FROM UNNEST(:recording_msids) recording_msid
     LEFT OUTER JOIN rf
               USING (recording_msid)
    """

    query_mbid = """
              SELECT recording_msid
                   , recording_mbid
                   , COALESCE(rf.score, 0) AS score
                FROM UNNEST(:recording_mbids) recording_mbid
     LEFT OUTER JOIN rf
               USING (recording_mbid)
    """

    # we cannot use single query here because recordings parameter passed to UNNEST should
    # not be empty so that we check which list is not empty and construct the query accordingly
    if recording_msids and recording_mbids:  # both msid and mbid list are not empty
        params["recording_msids"] = recording_msids
        params["recording_mbids"] = recording_mbids
        query_remaining = query_msid + " UNION " + query_mbid
    elif recording_msids:  # only msid list is not empty
        params["recording_msids"] = recording_msids
        query_remaining = query_msid
    else:  # only mbid list is not empty
        params["recording_mbids"] = recording_mbids
        query_remaining = query_mbid

    query = query_base + query_remaining
    result = db_conn.execute(text(query), params)
    return [Feedback(user_id=user_id, user_name=user_name, **row) for row in result.mappings()]
