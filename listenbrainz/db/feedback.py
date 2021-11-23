import sqlalchemy

from listenbrainz import db
from listenbrainz.db import timescale
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
    query = """ SELECT user_id,
                       "user".musicbrainz_id AS user_name,
                       recording_msid::text, score,
                       recording_feedback.created
                  FROM recording_feedback
                  JOIN "user"
                    ON "user".id = recording_feedback.user_id
                 WHERE user_id = :user_id """

    if score:
        query += " AND score = :score"
        args["score"] = score

    query += """ ORDER BY recording_feedback.created DESC
                 LIMIT :limit OFFSET :offset """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        feedback = [Feedback(**dict(row)) for row in result.fetchall()]

    if metadata and len(feedback) > 0:
        msids = [f.recording_msid for f in feedback]
        index = {f.recording_msid: f for f in feedback}

        # Fetch the artist and track names from MSB
        with msb_db.engine.connect() as connection:
            try:
                msb_recordings = load_recordings_from_msids(connection, msids)
            except NoDataFoundException:
                msb_recordings = []

        artist_msids = {}
        if msb_recordings:
            for rec in msb_recordings:
                index[rec["ids"]["recording_msid"]].track_metadata = {
                    "artist_name": rec["payload"]["artist"],
                    "release_name": rec["payload"].get("release_name", ""),
                    "track_name": rec["payload"]["title"]}
                artist_msids[rec["ids"]["recording_msid"]
                             ] = rec["ids"]["artist_msid"]

        # Fetch the mapped MBIDs from the mapping
        query = """SELECT recording_msid::TEXT, m.recording_mbid::TEXT, release_mbid::TEXT, artist_mbids::TEXT[]
                     FROM mbid_mapping m
                     JOIN mbid_mapping_metadata mm
                       ON m.recording_mbid = mm.recording_mbid
                    WHERE recording_msid in :msids
                 ORDER BY recording_msid"""

        with timescale.engine.connect() as connection:
            result = connection.execute(
                sqlalchemy.text(query), msids=tuple(msids))
            for row in result.fetchall():
                if row["recording_mbid"] is not None:
                    index[row["recording_msid"]].track_metadata['additional_info'] = {
                        "recording_mbid": row["recording_mbid"],
                        "release_mbid": row["release_mbid"],
                        "artist_mbids": row["artist_mbids"],
                        "artist_msid": artist_msids[row["recording_msid"]]}

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


def get_feedback_for_recording(recording_msid: str, limit: int, offset: int, score: int = None) -> List[Feedback]:
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
    query = """ SELECT user_id,
                       "user".musicbrainz_id AS user_name,
                       recording_msid::text, score,
                       recording_feedback.created
                  FROM recording_feedback
                  JOIN "user"
                    ON "user".id = recording_feedback.user_id
                 WHERE recording_msid = :recording_msid """

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


def get_feedback_for_multiple_recordings_for_user(user_id: int, recording_list: List[str]) -> List[Feedback]:
    """ Get a list of recording feedback given by the user for given recordings

        Args:
            user_id: the row ID of the user in the DB
            recording_list: list of recording_msid for which feedback records are to be obtained
                            - if record is present then return it
                            - if record is not present then return a pseudo record with score = 0

        Returns:
            A list of Feedback objects
    """

    args = {"user_id": user_id, "recording_list": recording_list}
    query = """ WITH rf AS (
              SELECT user_id, recording_msid::text, score
                FROM recording_feedback
               WHERE recording_feedback.user_id=:user_id
                )
              SELECT COALESCE(rf.user_id, :user_id) AS user_id,
                     "user".musicbrainz_id AS user_name,
                     rec_msid AS recording_msid,
                     COALESCE(rf.score, 0) AS score
                FROM UNNEST(:recording_list) rec_msid
     LEFT OUTER JOIN rf
                  ON rf.recording_msid::text = rec_msid
                JOIN "user"
                  ON "user".id = :user_id """

    with db.engine.connect() as connection:
        result = connection.execute(sqlalchemy.text(query), args)
        return [Feedback(**dict(row)) for row in result.fetchall()]
